import apiClient from "./client";
import type { User } from "../types";

export async function getProfile(): Promise<User> {
  const { data } = await apiClient.get("/api/users/profile");
  return data;
}

export async function updateProfile(
  updates: Partial<Pick<User, "name" | "age" | "weight" | "fitness_goals">>,
): Promise<User> {
  const { data } = await apiClient.put("/api/users/profile", updates);
  return data;
}
