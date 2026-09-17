import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext.jsx";
import { clearToken, setToken } from "../api/client.js";
// Import the page module AFTER the fetch stub is installed per-test? No —
// module import only defines components; fetch only fires inside effects, so
// top-level import is deterministic.
import InterviewPage from "../pages/InterviewPage.jsx";

afterEach(() => {
  clearToken();
});

export const interviewId = "11111111-2222-4333-8444-555555555555";
export const questionId = "22222222-3333-4444-8555-666666666666";

export function jsonResponse(data, { status = 200 } = {}) {
  return { ok: status >= 200 && status < 300, status, statusText: "OK", headers: new Headers(), json: async () => data, text: async () => JSON.stringify(data) };
}

export function stubBackend(scenario) {
  const mock = vi.fn(async (url, init = {}) => scenario(String(url), init.method || "GET", init));
  vi.stubGlobal("fetch", mock);
  return mock;
}

// Pre-authenticated session: tests inject the in-memory token directly so no
// boot /auth/refresh + /auth/me fetch races can swallow API stubs.
export const TEST_SESSION = { user: { id: "u1", email: "a@b.c", full_name: "A", is_active: true }, token: "test-token" };

export function renderInterview() {
  // Token set synchronously here AND via initialSession effect ordering can
  // race the first query flush, so belt-and-braces: set the module token now.
  setToken(TEST_SESSION.token);
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        // jsdom has no IntersectionObserver/document focus semantics; force
        // queries to run immediately and deterministically in tests.
        staleTime: 0,
      },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider initialSession={TEST_SESSION}>
        <MemoryRouter initialEntries={[`/interview/${interviewId}`]}>
          <Routes>
            <Route path="/interview/:interviewId" element={<InterviewPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

export const currentPayload = (overrides = {}) => ({
  interview_id: interviewId,
  status: "WAITING_FOR_ANSWER",
  order_index: 0,
  total_questions: 5,
  question_id: questionId,
  question_type: "TECHNICAL",
  question_text: "Explain event loops.",
  answer_allowed: true,
  follow_up: null,
  ...overrides,
});

describe("interview rendering + idempotency", () => {
  it("renders the server question with no invented rubric/metadata", async () => {
    const seen = [];
    const fetchMock = stubBackend((u) => {
      seen.push(u);
      if (u.endsWith(`/interviews/${interviewId}`)) {
        return jsonResponse({ id: interviewId, status: "WAITING_FOR_ANSWER", started_at: new Date().toISOString() });
      }
      if (u.endsWith(`/interviews/${interviewId}/current`)) return jsonResponse(currentPayload());
      if (u.endsWith(`/interviews/${interviewId}/transcript`)) return jsonResponse([]);
      return jsonResponse({}, { status: 404 });
    });
    renderInterview();
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(1), { timeout: 5000 });
    expect(await screen.findByText("Explain event loops.", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByText(/rubric/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/expected concept/i)).not.toBeInTheDocument();
  });

  it("reuses the SAME key when retrying the same submission", async () => {
    const user = userEvent.setup();
    const postedKeys = [];
    stubBackend((u, method, init) => {
      if (u.endsWith(`/interviews/${interviewId}`)) {
        return jsonResponse({ id: interviewId, status: "WAITING_FOR_ANSWER", started_at: new Date().toISOString() });
      }
      if (u.endsWith(`/interviews/${interviewId}/current`)) return jsonResponse(currentPayload());
      if (u.endsWith(`/interviews/${interviewId}/transcript`)) return jsonResponse([]);
      if (u.endsWith(`/interviews/${interviewId}/answers`)) {
        postedKeys.push(init.headers?.["Idempotency-Key"]);
        if (postedKeys.length === 1) throw new TypeError("network down");
        return jsonResponse({ answer_id: "a-1", attempt_number: 1, status: "EVALUATING", is_duplicate: false, accepted: true }, { status: 202 });
      }
      return jsonResponse({}, { status: 404 });
    });
    renderInterview();
    await screen.findByText("Explain event loops.");
    await user.type(screen.getByLabelText(/your answer/i), "The event loop schedules callbacks.");
    await user.click(screen.getByRole("button", { name: /send answer/i }));
    await waitFor(() => expect(screen.getByText(/cannot reach|connection/i)).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /send answer/i }));
    await waitFor(() => expect(postedKeys).toHaveLength(2));
    expect(postedKeys[0]).toBeTruthy();
    expect(postedKeys[1]).toBe(postedKeys[0]);
  });
});
