import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, UNAUTHORIZED_EVENT } from "../api/client";
import { clearToken, getToken } from "../api/auth";
import type { AuthUser } from "../api/types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  // starts true: on first load we don't yet know if a stored token is
  // still valid, so routes must wait for this to resolve before deciding
  // whether to redirect to /login (otherwise a refresh would always
  // briefly bounce a logged-in user to the login screen)
  const [loading, setLoading] = useState(true);

  async function loadCurrentUser() {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.getMe();
      setUser(me);
    } catch {
      // token was invalid/expired -- request() already cleared it
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCurrentUser();

    const onUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  async function login(email: string, password: string) {
    await api.login(email, password);
    await loadCurrentUser();
  }

  async function signup(email: string, password: string) {
    await api.signup(email, password);
    await loadCurrentUser();
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
