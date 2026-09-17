import { api } from "./client";

/** GET /roles -> [{ role, interview_types, difficulties, languages }] */
export function getRoles() {
  return api.get("/roles");
}
