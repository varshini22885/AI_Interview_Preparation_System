import { describe, expect, it, vi } from "vitest";
import { ApiError, clearToken } from "../api/client.js";
import { jsonResponse } from "./helpers.js";

describe("API client error contract", () => {
  it("parses the backend envelope and preserves request_id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ error: { code: "INTERVIEW_NOT_FOUND", message: "Not found.", request_id: "req-abc" } }, { status: 404 })),
    );
    const { api } = await import("../api/client.js");
    clearToken();
    try {
      await api.get("/interviews/missing");
      expect.unreachable("should throw");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(404);
      expect(err.code).toBe("INTERVIEW_NOT_FOUND");
      expect(err.requestId).toBe("req-abc");
    }
  });

  it("maps network failure to NETWORK_ERROR", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("boom");
      }),
    );
    const { api } = await import("../api/client.js");
    clearToken();
    await expect(api.get("/roles")).rejects.toMatchObject({ status: 0, code: "NETWORK_ERROR" });
  });

  it("refreshes once then retries the original request", async () => {
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        calls.push(String(url));
        if (String(url).endsWith("/auth/refresh")) return jsonResponse({ access_token: "new", expires_in: 900 });
        if (calls.filter((u) => u.endsWith("/auth/me")).length === 1) {
          return jsonResponse({ error: { code: "UNAUTHENTICATED", message: "Expired." } }, { status: 401 });
        }
        return jsonResponse({ id: "u1", email: "a@b.c" });
      }),
    );
    const client = await import("../api/client.js");
    client.setToken("stale");
    const me = await client.api.get("/auth/me");
    expect(me.email).toBe("a@b.c");
    expect(calls.filter((u) => u.endsWith("/auth/refresh"))).toHaveLength(1);
  });
});
