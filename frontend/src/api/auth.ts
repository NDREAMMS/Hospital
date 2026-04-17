import { apiClient } from "./client";

export type LoginPayload = { username: string; password: string };
export type LoginResponse = { token: string };

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/login/", payload);
  return response.data;
}
