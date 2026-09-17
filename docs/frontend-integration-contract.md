# Frontend Integration Contract

## Authentication

Register and login through `/api/v1/auth/*`. Send the in-memory access token as `Authorization: Bearer <token>` for REST calls. Refresh uses the backend HttpOnly cookie.

## Interview and realtime session

Create an interview, poll `GET /api/v1/interviews/{id}` until `READY`, then call `POST /api/v1/interviews/{id}/start`. After the interview is active, create a session:

```json
POST /api/v1/interviews/{id}/realtime/session
{
  "session_id": "uuid",
  "interview_id": "uuid",
  "status": "ACTIVE",
  "websocket_path": "/api/v1/interviews/{id}/realtime/ws?session_id=uuid"
}
```

Connect using the returned path and the short-lived access token as `access_token` query parameter. WebSocket authentication is required; do not send provider credentials.

## Server events

On connection the server sends:

```json
{"type":"session_ack","session_id":"uuid","interview_id":"uuid","status":"WAITING_FOR_ANSWER"}
{"type":"question_started","question_id":"uuid","text":"...","status":"WAITING_FOR_ANSWER"}
```

The server may send `heartbeat_ack`, `face_status_ack`, `audio_ack`, `transcript_final`, `evaluation_started`, and `error`. The REST interview status remains authoritative for evaluation, follow-up, completion, and report polling.

When NVIDIA speech is configured, `question_started` is followed by `audio_started` and one or more `audio_chunk` events containing base64 WAV audio. TTS is request-based in this backend; ASR is true streaming through an NVIDIA Speech NIM Riva gRPC stream and may emit `transcript_partial` events before `transcript_final`.

## Client events

```json
{"type":"session_start"}
{"type":"heartbeat"}
{"type":"face_status","timestamp":"2026-09-17T10:00:00Z","face_present":true,"face_count":1,"head_pose":{"yaw":1.4,"pitch":-0.2}}
{"type":"audio_start"}
{"type":"audio_chunk","data":"base64-or-provider-frame"}
{"type":"audio_end"}
{"type":"answer_complete","question_id":"uuid","transcript":"Final transcript","idempotency_key":"unique-key-123"}
{"type":"session_end"}
```

All events reject unknown fields. Maximum event size is 256 KiB. Face events accept at most two faces and yaw/pitch in `-90..90`; raw frames are not persisted. Audio chunks must be base64 and remain within the configured chunk/session limits.

`answer_complete` is the authoritative transcript boundary. It uses the same answer service and idempotency rules as REST submission, then emits `evaluation_started`. Poll the interview endpoint for `FOLLOW_UP_REQUIRED`, `WAITING_FOR_ANSWER`, `COMPLETED`, `REPORT_GENERATING`, `REPORT_READY`, or `FAILED`. Retrieve a ready report with `GET /api/v1/reports/{id}`.

## Reconnect

A refresh or disconnect does not reset interview state. Reuse the active session ID, reconnect with a valid access token, and treat the new `session_ack` plus `question_started` event as authoritative. If the token expires, refresh through REST before reconnecting.

## Privacy

Camera processing remains client-side. Send compact face events only. Do not send API keys, raw camera frames, passwords, refresh tokens, or full provider prompts.
