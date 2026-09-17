/**
 * Centralized HTTP client.
 * - Base URL from environment (VITE_API_BASE_URL), never hardcoded.
 * - Maps backend error envelope { error: { code, message, request_id } } to ApiError.
 * - Access token lives in memory ONLY. Refresh token stays in the backend's
 *   HttpOnly cookie; the JSON refresh_token field is intentionally discarded.
 * - 401 => single-flight refresh => one retry of the original request.
 * - Never logs tokens, resume contents, or answers.
 */

const BASE_URL = import.meta.env?.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  constructor(status, code, message, requestId = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

let accessToken = null;
let refreshInFlight = null;
let unauthorizedHandler = null;

export function setToken(token) {
  accessToken = token || null;
}

export function clearToken() {
  accessToken = null;
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === "function" ? handler : null;
}

function notifyUnauthorized() {
  clearToken();
  if (unauthorizedHandler) unauthorizedHandler();
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function toApiError(body, status) {
  const envelope = body && body.error ? body.error : null;
  return new ApiError(
    status,
    envelope?.code || `HTTP_${status}`,
    envelope?.message || "Request failed.",
    envelope?.request_id || null,
  );
}

/** Try to rotate the refresh cookie into a new in-memory access token. */
async function tryRefresh() {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) return false;
      const data = await response.json();
      // data.refresh_token is intentionally NOT stored or logged.
      accessToken = data.access_token || null;
      return Boolean(accessToken);
    } catch {
      return false;
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

/** Restore a session from the refresh cookie (used on app boot). */
export async function restoreSession() {
  return tryRefresh();
}

const AUTH_BYPASS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

async function request(path, { method = "GET", body, formData, headers = {}, retry = true } = {}) {
  const requestHeaders = { ...headers };
  if (accessToken) requestHeaders.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) requestHeaders["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      credentials: "include",
      body: formData ? formData : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the server. Check your connection and try again.");
  }

  if (response.status === 401 && retry && !AUTH_BYPASS.some((p) => path.startsWith(p))) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request(path, { method, body, formData, headers, retry: false });
    }
    notifyUnauthorized();
  }

  if (!response.ok) {
    throw toApiError(await safeJson(response), response.status);
  }
  if (response.status === 204) return null;
  return safeJson(response);
}

export const api = {
  get: (path) => request(path),
  post: (path, body, options = {}) => request(path, { method: "POST", body, ...options }),
  postForm: (path, formData) => request(path, { method: "POST", formData }),
  del: (path) => request(path, { method: "DELETE" }),
};
