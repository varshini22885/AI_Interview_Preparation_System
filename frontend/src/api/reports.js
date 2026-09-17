import { api } from "./client";

/** GET /reports/{interviewId} -> persisted report (409 REPORT_NOT_READY until then) */
export function getReport(interviewId) {
  return api.get(`/reports/${interviewId}`);
}
