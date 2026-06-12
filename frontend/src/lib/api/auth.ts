/**
 * API client cho 4 endpoint accounts (login/refresh/logout/me).
 *
 * Cookie-based: browser tự gửi `access_token` + `csrftoken` cookies.
 * Không cần Authorization header. CSRF qua `X-CSRFToken` (axios tự lo).
 */
import { apiClient } from "./client";

import type { AuthUser, LoginResponse, MeResponse } from "@/lib/types/auth";

export async function login(
  username: string,
  password: string,
): Promise<AuthUser> {
  const response = await apiClient.post<LoginResponse>("/auth/login/", {
    username,
    password,
  });
  return response.data.user;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout/");
}

/** Manually trigger refresh. Hook bình thường KHÔNG cần — axios interceptor lo
 * sẵn cho mọi request bị 401. Helper này expose để test smoke. */
export async function refresh(): Promise<void> {
  await apiClient.post("/auth/refresh/");
}

export async function getMe(): Promise<MeResponse> {
  const response = await apiClient.get<MeResponse>("/auth/me/");
  return response.data;
}
