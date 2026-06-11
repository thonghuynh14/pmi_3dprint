/** @type {import('next').NextConfig} */
const nextConfig = {
  // DRF bắt buộc trailing slash. Next.js nuốt mất dấu "/" cuối khi match `:path*`
  // → Django trả 301 (GET) / 500 (POST). Khắc phục: tự thêm "/" vào destination (dưới).
  // skipTrailingSlashRedirect: chặn Next 308-redirect phía browser (đỡ 1 vòng thừa).
  skipTrailingSlashRedirect: true,
  async rewrites() {
    // Proxy mọi call /api/* qua Next.js server sang Django chạy local.
    // Lợi ích: browser chỉ thấy 1 origin (cùng host với trang) → không dính CORS,
    // và demo qua ngrok chỉ cần 1 tunnel (tunnel port 3000, KHÔNG expose :8000).
    // Dùng 127.0.0.1 (không phải localhost) để né IPv6 ::1 trên Windows.
    const backendOrigin = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backendOrigin}/api/:path*/` }];
  },
};

export default nextConfig;
