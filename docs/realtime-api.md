# Realtime API

The realtime transport is a FastAPI WebSocket backed by a persisted `RealtimeInterviewSession`. PostgreSQL interview state remains authoritative; a session only represents connection/reconnect ownership.

## Lifecycle

1. Authenticate with REST.
2. Start a `READY` interview.
3. `POST /api/v1/interviews/{interview_id}/realtime/session`.
4. Connect to the returned WebSocket path with `access_token`.
5. Exchange strict JSON events.
6. Submit only final transcripts with `answer_complete`.
7. Poll REST for worker-owned evaluation and report states.

Unknown event types, malformed JSON, unknown fields, and events over 256 KiB return an `error` event. Ownership and session IDs are checked before accepting the connection. A client disconnect leaves the session active for reconnect.

Speech-to-text streaming and text-to-speech are intentionally not simulated. Audio is currently acknowledged as transport input and reports `STT_NOT_CONFIGURED` at `audio_end` until a configured provider adapter is enabled.
