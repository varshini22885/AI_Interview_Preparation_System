import { api } from "./client";

/**
 * GET /history -> { items, page, page_size, total }
 * filters: role, interviewType (TECHNICAL|BEHAVIORAL|MIXED), difficulty (EASY|MEDIUM|HARD|EXPERT)
 */
export function getHistory({ page = 1, pageSize = 10, role, interviewType, difficulty } = {}) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (role) params.set("role", role);
  if (interviewType) params.set("interview_type", interviewType);
  if (difficulty) params.set("difficulty", difficulty);
  return api.get(`/history?${params.toString()}`);
}
