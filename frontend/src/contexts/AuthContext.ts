import { createContext } from "react";

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  userName: string | null;
}

export interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
