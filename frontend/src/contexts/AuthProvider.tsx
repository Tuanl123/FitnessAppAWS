import { useCallback, useMemo, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { AuthContext, type AuthState } from "./AuthContext";

function readInitialState(): AuthState {
  if (typeof window === "undefined") {
    return { isAuthenticated: false, isLoading: false, userName: null };
  }
  const token = localStorage.getItem("access_token");
  return {
    isAuthenticated: !!token,
    isLoading: false,
    userName: localStorage.getItem("user_name"),
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(readInitialState);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await authApi.login(email, password);
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    setState({ isAuthenticated: true, isLoading: false, userName: null });
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const res = await authApi.register(email, password, name);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      localStorage.setItem("user_name", res.name);
      setState({ isAuthenticated: true, isLoading: false, userName: res.name });
    },
    [],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_name");
    setState({ isAuthenticated: false, isLoading: false, userName: null });
  }, []);

  const value = useMemo(
    () => ({ ...state, login, register, logout }),
    [state, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
