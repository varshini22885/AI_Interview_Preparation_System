import { createContext, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import { clearToken, restoreSession, setToken, setUnauthorizedHandler } from "../api/client";

/**
 * Session state: the short-lived access token is held in memory only
 * (never localStorage/sessionStorage); the refresh token lives in the
 * backend's HttpOnly cookie. Tests may inject an authenticated session via
 * the `initialSession` prop ({ user, token }) to avoid boot-fetch races.
 */

const AuthContext = createContext(null);

export function AuthProvider({ children, initialSession = null }) {
  const [user, setUser] = useState(initialSession?.user ?? null);
  // loading | authenticated | unauthenticated
  const [status, setStatus] = useState(initialSession ? "authenticated" : "loading");

  useEffect(() => {
    if (initialSession?.token) setToken(initialSession.token);
  }, [initialSession]);

  useEffect(() => {
    if (initialSession) return undefined;
    setUnauthorizedHandler(() => {
      setUser(null);
      setStatus("unauthenticated");
    });
    let cancelled = false;
    (async () => {
      const restored = await restoreSession();
      if (cancelled) return;
      if (!restored) {
        setStatus("unauthenticated");
        return;
      }
      try {
        const me = await authApi.getMe();
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        clearToken();
        setStatus("unauthenticated");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialSession]);

  const value = useMemo(
    () => ({
      user,
      status,
      async login(email, password) {
        const { accessToken } = await authApi.login(email, password);
        setToken(accessToken);
        const me = await authApi.getMe();
        setUser(me);
        setStatus("authenticated");
        return me;
      },
      async register(email, fullName, password) {
        await authApi.registerUser({ email, fullName, password });
        return this.login(email, password);
      },
      async logout() {
        try {
          await authApi.logout();
        } finally {
          clearToken();
          setUser(null);
          setStatus("unauthenticated");
        }
      },
    }),
    [user, status],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
