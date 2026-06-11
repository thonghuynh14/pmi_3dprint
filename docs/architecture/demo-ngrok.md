# Demo nhanh qua ngrok

Cách share bản đang chạy trên máy bạn cho người khác **dùng thử** qua 1 link public,
không cần deploy cloud. Dùng cho demo tạm thời với người tin tưởng — **không phải hosting thật**.

> Trạng thái app: mới có **CRUD Product**, và còn các deferred items về bảo mật
> (chưa có RBAC, token ở localStorage, dev login). Vì vậy chỉ share cho người tin tưởng.

## ngrok hoạt động thế nào ở đây

Chỉ tunnel **1 cổng** (Next.js `:3000`). Next.js proxy các call `/api/*` về Django local
(`127.0.0.1:8000`) — cấu hình ở [next.config.mjs](../../frontend/next.config.mjs).

```
Khách → https://xxx.ngrok-free.app   (tunnel → Next.js :3000)
             ├─ UI            → Next.js
             └─ /api/*  proxy → 127.0.0.1:8000  (Django, KHÔNG public)
```

→ Không dính CORS (cùng origin), chỉ tốn 1 tunnel (đủ cho ngrok free), `/admin` Django chỉ bạn dùng được ở local.

## Trade-off cần biết trước

- **Máy bạn = server**: PC phải bật + cả 3 tiến trình (Docker, Django, Next.js, ngrok) chạy suốt thời gian demo.
- **URL đổi mỗi lần restart** ngrok (free tier random subdomain). Muốn URL cố định → claim 1 *static domain* free trong ngrok dashboard.
- **Trang cảnh báo ngrok**: lần đầu khách bấm "Visit Site" 1 lần, sau đó hết hiện (cookie session).
- **Giới hạn free**: vài chục request/phút — ổn cho demo vài người, không cho tải nặng.

## Yêu cầu trước

1. Docker Desktop đang chạy (`docker compose up -d` → postgres/redis/minio). Xem note dev-environment.
2. ngrok đã cài + đã add authtoken:
   ```powershell
   winget install ngrok.ngrok          # hoặc: choco install ngrok / scoop install ngrok
   ngrok update                        # ⚠️ winget hay cài bản cũ (vd 3.3.1); account yêu cầu >= 3.20
   ngrok config add-authtoken <TOKEN>  # lấy ở https://dashboard.ngrok.com (đăng ký free)
   ```
   > **PATH trên Windows**: sau khi cài, terminal đang mở (kể cả terminal tích hợp VS Code)
   > vẫn giữ PATH cũ → gõ `ngrok` báo "not recognized". Cách nhanh nhất, nạp lại PATH cho
   > terminal hiện tại:
   > ```powershell
   > $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
   > ```
   > Hoặc thoát hẳn VS Code rồi mở lại (mở tab terminal mới thôi là chưa đủ).
3. `frontend/.env.local` đặt API về relative để kích hoạt proxy:
   ```
   NEXT_PUBLIC_API_URL=/api
   ```
   (Để dev bình thường thì set lại `http://localhost:8000/api`.)

## Chạy (4 terminal)

```powershell
# 1) Docker services (nếu chưa up)
docker compose up -d

# 2) Backend Django  (cd backend; venv activated)
python manage.py runserver 8000

# 3) Frontend Next.js  (cd frontend)
npm run dev

# 4) ngrok — tunnel cổng Next.js
ngrok http 3000
```

ngrok in ra dòng `Forwarding  https://xxxx-xx.ngrok-free.app -> http://localhost:3000`.
**Gửi link `https://xxxx-xx.ngrok-free.app` đó cho người dùng.**

## Người dùng đăng nhập thế nào

- Vào link → trang `/login`.
- Hiện chỉ có user dev `smoke` / `smokepass` (superuser, chưa có RBAC nên account nào cũng full quyền).
  - Share cẩn thận, hoặc tạo account demo riêng qua Django admin (`http://127.0.0.1:8000/admin`, chỉ ở máy bạn).
- Sau login, quản lý sản phẩm ở `/admin/products`.

## Dừng

Đóng terminal ngrok (link chết ngay), rồi dừng Next.js / Django. Docker: `docker compose down` nếu muốn.

## Khi nào nên chuyển sang hosting thật

Khi cần **chạy 24/7, không phụ thuộc máy bạn, URL cố định, có RBAC** → deploy lên
Render/Railway + Supabase (đã chốt trong [tech-stack.md](tech-stack.md)). Việc đó nên đi kèm
feature `accounts/RBAC` để khoá quyền trước khi mở cho người dùng thật.
