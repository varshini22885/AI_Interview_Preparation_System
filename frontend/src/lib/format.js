/** Display-only helpers. No business rules live here. */

export const INTERVIEW_TYPE_LABELS = {
  TECHNICAL: "Technical",
  BEHAVIORAL: "Behavioral",
  MIXED: "Mixed",
};

export const DIFFICULTY_LABELS = {
  EASY: "Easy",
  MEDIUM: "Medium",
  HARD: "Hard",
  EXPERT: "Expert",
};

export const PERSONA_LABELS = {
  FRIENDLY: "Friendly",
  PROFESSIONAL: "Professional",
  STRICT: "Strict",
};

/** Deterministic presentation label derived from a REAL persisted score. */
export function scoreBandLabel(score) {
  if (score === null || score === undefined) return "Pending";
  if (score >= 80) return "Strong performance";
  if (score >= 60) return "Developing";
  return "Needs work";
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

/** Elapsed mm:ss since a server timestamp. Presentation only — never state. */
export function formatElapsed(startedAtIso, nowMs) {
  if (!startedAtIso) return null;
  const start = new Date(startedAtIso).getTime();
  if (Number.isNaN(start)) return null;
  const seconds = Math.max(0, Math.floor(((nowMs ?? Date.now()) - start) / 1000));
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function pad2(n) {
  return String(n).padStart(2, "0");
}

/** UUID for idempotency keys (with non-secure-context fallback for tests). */
export function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.trunc(Math.random() * 16);
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
