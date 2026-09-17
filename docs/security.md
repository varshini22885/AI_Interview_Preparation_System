# Backend Security Notes

REST resources enforce authenticated ownership. WebSocket connections require an access token, interview ID, and active persisted session belonging to the same user. Invalid ownership returns a generic unavailable response.

Access tokens remain client memory; refresh tokens are HttpOnly cookies. Provider keys, storage credentials, database credentials, resumes, transcripts, prompts, and raw audio must not be logged or sent to the browser. Face events are compact, range-validated status data; no biometric templates or inferences are stored.

Upload extensions and size are restricted and storage keys are generated server-side. Production readiness probes PostgreSQL and Redis and returns HTTP 503 when either dependency is unavailable. Configure production secrets through the environment, never source files.
