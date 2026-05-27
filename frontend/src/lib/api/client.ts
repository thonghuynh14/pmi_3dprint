/**
 * API client skeleton — axios instance + JWT interceptors.
 *
 * Auth flow (xem docs/architecture/tech-stack.md - Auth strategy):
 *   1. Mỗi request gắn Bearer {access_token}
 *   2. 401 → tự refresh qua /api/v1/auth/refresh/ (refresh token trong httpOnly cookie)
 *   3. Retry request gốc, nếu vẫn fail → throw để UI redirect login
 *
 * Endpoint thật mount dưới /api/v1/ — xem backend/config/urls.py.
 * Module này CHƯA bind endpoint cụ thể: từng feature sẽ tạo file riêng
 * (vd src/lib/api/products.ts) gọi qua axios instance này.
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "http://localhost:8000/api";

// =============================================================================
// Token storage
// =============================================================================
// MVP: lưu access token trong localStorage để survive page refresh khi
// chưa có feature `accounts/auth UI` (defer per OQ-2). Production sẽ
// chuyển sang in-memory + httpOnly refresh cookie.
const LS_KEY = "pim_access_token";
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(LS_KEY, token);
  } else {
    window.localStorage.removeItem(LS_KEY);
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

/** Đọc token từ localStorage vào memory. Gọi 1 lần ở client mount
 * (xem components/providers.tsx hoặc app/(admin)/layout.tsx). */
export function bootstrapAccessTokenFromStorage(): void {
  if (typeof window === "undefined") return;
  if (accessToken) return;
  const stored = window.localStorage.getItem(LS_KEY);
  if (stored) accessToken = stored;
}

// =============================================================================
// Axios instance
// =============================================================================
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/v1`,
  timeout: 30_000,
  withCredentials: true, // refresh token cookie
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// =============================================================================
// 401 refresh logic
// =============================================================================
type RetriableConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await axios.post<{ access: string }>(
        `${API_BASE_URL}/v1/auth/refresh/`,
        {},
        { withCredentials: true },
      );
      setAccessToken(response.data.access);
      return response.data.access;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    if (!original || error.response?.status !== 401 || original._retry) {
      throw error;
    }

    original._retry = true;
    const newToken = await refreshAccessToken();
    if (!newToken) {
      // BE sẽ redirect login - tuỳ feature middleware xử
      throw error;
    }

    original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` };
    return apiClient.request(original);
  },
);
