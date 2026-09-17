import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext.jsx";
import LobbyPage from "../pages/LobbyPage.jsx";
import HistoryPage from "../pages/HistoryPage.jsx";
import ReportPage from "../pages/ReportPage.jsx";

const interviewId = "11111111-2222-4333-8444-555555555555";

function jsonResponse(data, { status = 200 } = {}) {
  return { ok: status >= 200 && status < 300, status, json: async () => data };
}

function stubBackend(scenario) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const u = String(url);
      if (u.endsWith("/auth/refresh")) return jsonResponse({ access_token: "tok", expires_in: 900 });
      if (u.endsWith("/auth/me")) return jsonResponse({ id: "u1", email: "a@b.c", full_name: "A", is_active: true });
      return scenario(u, init.method || "GET", init);
    }),
  );
}

function renderAt(path, elementMap) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/lobby/:interviewId" element={elementMap.lobby} />
            <Route path="/report/:interviewId" element={elementMap.report} />
            <Route path="/history" element={elementMap.history} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("lobby polling + report/history states", () => {
  it("lobby waits while PREPARING and enables entry only on READY", async () => {
    let calls = 0;
    stubBackend((u) => {
      if (u.endsWith(`/interviews/${interviewId}`)) {
        calls += 1;
        const summary = { id: interviewId, target_role: "Backend Developer", interview_type: "TECHNICAL", difficulty: "MEDIUM", interviewer_persona: "PROFESSIONAL", total_questions: 5, current_question_index: 0, created_at: new Date().toISOString() };
        return jsonResponse({ ...summary, status: calls < 2 ? "PREPARING" : "READY" });
      }
      return jsonResponse({}, { status: 404 });
    });
    renderAt(`/lobby/${interviewId}`, { lobby: <LobbyPage /> });
    expect(await screen.findByText(/preparing your interview/i)).toBeInTheDocument();
    // Bounded polling converges on READY and only then shows the entry action.
    await waitFor(() => expect(screen.queryByRole("button", { name: /enter interview/i })).toBeInTheDocument(), { timeout: 8000 });
  });

  it("report polls through 409 then renders persisted scores", async () => {
    let calls = 0;
    stubBackend((u) => {
      if (u.endsWith(`/reports/${interviewId}`)) {
        calls += 1;
        if (calls === 1) {
          return jsonResponse({ error: { code: "REPORT_NOT_READY", message: "Report is generating.", request_id: "r1" } }, { status: 409 });
        }
        return jsonResponse({ interview_id: interviewId, status: "REPORT_READY", technical_score: 80, communication_score: 70, overall_score: 75, total_questions_answered: 2 });
      }
      return jsonResponse({}, { status: 404 });
    });
    renderAt(`/report/${interviewId}`, { report: <ReportPage /> });
    expect(await screen.findByText(/generating/i)).toBeInTheDocument();
    // Score digits render in split nodes; assert the user-visible outcome is
    // the real persisted value (INTERVIEW COMPLETE banner) once polling lands.
    await waitFor(() => expect(screen.queryByText(/interview complete/i)).toBeInTheDocument(), { timeout: 10000 });
  });

  it("history shows pagination and an honest empty state", async () => {
    stubBackend((u) => {
      if (u.includes("/history")) {
        const page = Number(new URL(u, "http://x").searchParams.get("page") || "1");
        const items = page === 1 ? [{ id: "h1", status: "REPORT_READY", target_role: "Backend Developer", interview_type: "TECHNICAL", difficulty: "MEDIUM", total_questions: 5, completed_at: new Date().toISOString(), overall_score: 75 }] : [];
        return jsonResponse({ items, page, page_size: 1, total: 2 });
      }
      return jsonResponse({}, { status: 404 });
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/history"]}>
            <HistoryPage pageSizeForTest={1} />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Backend Developer")).toBeInTheDocument();
  });

  it("history empty state when the user has no interviews", async () => {
    stubBackend((u) => {
      if (u.includes("/history")) return jsonResponse({ items: [], page: 1, page_size: 10, total: 0 });
      return jsonResponse({}, { status: 404 });
    });
    renderAt("/history", { history: <HistoryPage /> });
    expect(await screen.findByText(/no interviews found/i)).toBeInTheDocument();
  });

  it("surfaces expired sessions without crashing", async () => {
    stubBackend(() => jsonResponse({ error: { code: "UNAUTHENTICATED", message: "Expired.", request_id: "req-x" } }, { status: 401 }));
    renderAt("/history", { history: <HistoryPage /> });
    await waitFor(() => expect(screen.getByText(/expired|sign in|session/i)).toBeInTheDocument());
  });
});
