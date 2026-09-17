"""Provider-neutral speech interfaces.

Implementations must be configured with backend-only credentials. No default
implementation fabricates transcripts or audio.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TranscriptEvent:
    text: str
    final: bool


class SpeechToTextProvider(Protocol):
    def start(self, *, audio_format: str) -> None: ...
    def process_chunk(self, chunk: bytes) -> list[TranscriptEvent]: ...
    def finish(self) -> TranscriptEvent: ...
    def close(self) -> None: ...


class TextToSpeechProvider(Protocol):
    def synthesize(self, text: str, *, audio_format: str) -> bytes: ...


class UnconfiguredSpeechProvider:
    """Explicit failure until a selected provider supplies speech support."""

    def start(self, *, audio_format: str) -> None:
        raise RuntimeError("Speech-to-text provider is not configured")

    def process_chunk(self, chunk: bytes) -> list[TranscriptEvent]:
        raise RuntimeError("Speech-to-text provider is not configured")

    def finish(self) -> TranscriptEvent:
        raise RuntimeError("Speech-to-text provider is not configured")

    def close(self) -> None:
        return None

    def synthesize(self, text: str, *, audio_format: str) -> bytes:
        raise RuntimeError("Text-to-speech provider is not configured")


class NvidiaSpeechToTextProvider:
    """True streaming ASR adapter for an NVIDIA Speech NIM via Riva gRPC."""

    def __init__(self, *, server: str, model: str, use_ssl: bool, language_code: str = "en-US") -> None:
        self.server = server
        self.model = model
        self.use_ssl = use_ssl
        self.language_code = language_code
        self._queue = None
        self._responses = None
        self._thread = None

    def start(self, *, audio_format: str) -> None:
        import queue
        import threading

        try:
            import riva.client
        except ImportError as exc:
            raise RuntimeError("NVIDIA Riva client is not installed") from exc
        self._queue = queue.Queue()
        self._response_queue = queue.Queue()
        auth = riva.client.Auth(uri=self.server, use_ssl=self.use_ssl)
        service = riva.client.ASRService(auth)
        config = riva.client.StreamingRecognitionConfig(
            config=riva.client.RecognitionConfig(language_code=self.language_code, model=self.model, max_alternatives=1),
            interim_results=True,
        )

        def audio_stream():
            while True:
                chunk = self._queue.get()
                if chunk is None:
                    return
                yield chunk

        self._responses = service.streaming_response_generator(audio_chunks=audio_stream(), streaming_config=config)
        self._thread = threading.Thread(target=self._consume, daemon=True)
        self._thread.start()

    def _consume(self) -> None:
        try:
            for response in self._responses:
                self._response_queue.put(response)
        except Exception as exc:
            self._response_queue.put(exc)

    def process_chunk(self, chunk: bytes) -> list[TranscriptEvent]:
        if self._queue is None:
            raise RuntimeError("ASR session is not started")
        self._queue.put(chunk)
        events = []
        while not self._response_queue.empty():
            response = self._response_queue.get_nowait()
            if isinstance(response, Exception):
                raise RuntimeError("NVIDIA ASR request failed") from response
            for result in getattr(response, "results", []) or []:
                alternatives = getattr(result, "alternatives", []) or []
                if alternatives:
                    events.append(TranscriptEvent(text=alternatives[0].transcript, final=bool(getattr(result, "is_final", False))))
        return events

    def finish(self) -> TranscriptEvent:
        if self._queue is None:
            raise RuntimeError("ASR session is not started")
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=30)
        events = []
        while not self._response_queue.empty():
            response = self._response_queue.get_nowait()
            if isinstance(response, Exception):
                raise RuntimeError("NVIDIA ASR request failed") from response
            for result in getattr(response, "results", []) or []:
                alternatives = getattr(result, "alternatives", []) or []
                if alternatives:
                    events.append(TranscriptEvent(text=alternatives[0].transcript, final=bool(getattr(result, "is_final", False))))
        final = next((event for event in reversed(events) if event.final), None)
        if final is None:
            raise RuntimeError("NVIDIA ASR returned no final transcript")
        return final

    def close(self) -> None:
        if self._queue is not None:
            self._queue.put(None)


class NvidiaTextToSpeechProvider:
    """Request-based offline synthesis through the documented Riva client."""

    def __init__(self, *, server: str, model: str, voice: str, use_ssl: bool, language_code: str = "en-US") -> None:
        self.server = server
        self.model = model
        self.voice = voice
        self.use_ssl = use_ssl
        self.language_code = language_code

    def synthesize(self, text: str, *, audio_format: str) -> bytes:
        if not text.strip() or len(text) > 2000:
            raise ValueError("TTS text must be 1-2000 characters")
        try:
            import riva.client
            from riva.client.proto.riva_audio_pb2 import AudioEncoding
        except ImportError as exc:
            raise RuntimeError("NVIDIA Riva client is not installed") from exc
        auth = riva.client.Auth(uri=self.server, use_ssl=self.use_ssl)
        service = riva.client.SpeechSynthesisService(auth)
        encoding = AudioEncoding.OGGOPUS if audio_format == "ogg_opus" else AudioEncoding.LINEAR_PCM
        response = service.synthesize(text, self.voice, self.language_code, sample_rate_hz=22050, encoding=encoding)
        return bytes(response.audio)


def get_speech_providers():
    from app.core.config import get_settings

    settings = get_settings()
    if settings.AI_PROVIDER != "nvidia":
        return UnconfiguredSpeechProvider(), UnconfiguredSpeechProvider()
    if not settings.NVIDIA_STT_MODEL or not settings.NVIDIA_TTS_MODEL or not settings.NVIDIA_TTS_VOICE:
        raise RuntimeError("NVIDIA speech models and voice must be configured")
    return (
        NvidiaSpeechToTextProvider(server=settings.NVIDIA_ASR_SERVER, model=settings.NVIDIA_STT_MODEL, use_ssl=settings.NVIDIA_SPEECH_USE_SSL),
        NvidiaTextToSpeechProvider(server=settings.NVIDIA_TTS_SERVER, model=settings.NVIDIA_TTS_MODEL, voice=settings.NVIDIA_TTS_VOICE, use_ssl=settings.NVIDIA_SPEECH_USE_SSL),
    )
