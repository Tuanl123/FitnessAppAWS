import apiClient from "./client";
import type { AuthTokens, RegisterResponse } from "../types";

export async function register(
  email: string,
  password: string,
  name: string,
): Promise<RegisterResponse> {
  const { data } = await apiClient.post("/api/users/auth/register", {
    email,
    password,
    name,
  });
  return data;
}

export async function login(
  email: string,
  password: string,
): Promise<AuthTokens> {
  const { data } = await apiClient.post("/api/users/auth/login", {
    email,
    password,
  });
  return data;
}

export async function refreshAccessToken(
  refreshToken: string,
): Promise<{ access_token: string }> {
  const { data } = await apiClient.post("/api/users/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}
