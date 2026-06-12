/**
 * Axios instance cho API client (cookie-based JWT auth).
 *
 * Token storage **HOÀN TOÀN ở httpOnly cookies** (BE set qua /auth/login/).
 * FE không touch token. Lợi ích:
 *   - XSS không steal được token.
 *   - Browser tự gửi cookies → không cần Authorization header.
 *   - State đơn giản (không Zustand store).
 *
 * Mutation (POST/PATCH/PUT/DELETE) cần `X-CSRFToken` header — axios tự
 * đọc cookie `csrftoken` (NON-httpOnly) qua `xsrfCookieName`.
 *
 * 401 → tự refresh qua `/auth/refresh/` → retry. Refresh fail (refresh
 * cookie cũng expired) → redirect `/login`.
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "http://localhost:8000/api";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/v1`,
  timeout: 30_000,
  // Browser tự gửi cookie cùng host (proxy /api/* qua Next.js → same-origin).
  withCredentials: true,
  // Axios tự đọc cookie csrftoken → gửi vào header X-CSRFToken cho mutation.
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ---------------------------------------------------------------------------
// 401 → refresh → retry
// ---------------------------------------------------------------------------
type RetriableConfig = AxiosRequestConfig & { _retry?: boolean };

/** Lock concurrent refresh — đa request 401 cùng lúc chỉ refresh 1 lần. */
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessCookie(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      await axios.post(
        `${API_BASE_URL}/v1/auth/refresh/`,
        {},
        { withCredentials: true },
      );
      return true;
    } catch {
      return false;
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

    // Đừng refresh khi chính endpoint /auth/refresh/ hoặc /auth/login/
    // trả 401 (tránh vòng lặp).
    if (
      original.url?.includes("/auth/refresh") ||
      original.url?.includes("/auth/login")
    ) {
      throw error;
    }

    original._retry = true;
    const ok = await refreshAccessCookie();
    if (!ok) {
      // Refresh fail → redirect login (only client-side, server render skip).
      if (typeof window !== "undefined") {
        const next = encodeURIComponent(
          window.location.pathname + window.location.search,
        );
        window.location.href = `/login?next=${next}`;
      }
      throw error;
    }

    return apiClient.request(original);
  },
);
