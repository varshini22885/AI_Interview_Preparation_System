# AI Providers

`AI_PROVIDER` selects the backend provider. `test` is deterministic and forbidden when `APP_ENV=production`. `openai` and `anthropic` use the existing vendor adapter. `nvidia` uses NVIDIA's OpenAI-compatible chat endpoint through `NVIDIA_BASE_URL`, with `NVIDIA_API_KEY` and `NVIDIA_LLM_MODEL` kept server-side.

Every text operation returns a strict Pydantic schema. The application computes authoritative scores from persisted evaluation dimensions; model-provided report scores are narrative metadata only. Provider errors and malformed output remain failures after bounded service retries.

Speech uses the official NVIDIA Riva client when `AI_PROVIDER=nvidia`. ASR is true streaming through `ASRService.streaming_response_generator`; TTS is request-based offline synthesis through `SpeechSynthesisService.synthesize`, returning WAV or OGG/Opus bytes. Configure NIM server addresses, served model names, and a voice from the deployed service. The documented examples use Parakeet CTC 1.1b English for ASR and Magpie multilingual voices for TTS, but model selection remains environment-driven.
