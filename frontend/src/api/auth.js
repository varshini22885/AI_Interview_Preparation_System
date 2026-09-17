import { api } from "./client";

/** POST /auth/register -> user */
export function registerUser({ email, fullName, password }) {
  return api.post("/auth/register", { email, full_name: fullName, password });
}

/** POST /auth/login -> { access_token, expires_in } (refresh token stays in HttpOnly cookie) */
export async function login(email, password) {
  const data = await api.post("/auth/login", { email, password });
  return { accessToken: data.access_token, expiresIn: data.expires_in };
}

/** GET /auth/me -> user */
export function getMe() {
  return api.get("/auth/me");
}

/** POST /auth/logout -> revoke refresh token + clear cookie (204) */
export function logout() {
  return api.post("/auth/logout");
}
