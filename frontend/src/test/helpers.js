/** Shared test helpers for API client + page tests.
 *  Only contains test plumbing (no production business logic).
 */
export function jsonResponse(data, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "OK",
    headers: new Headers(),
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}
