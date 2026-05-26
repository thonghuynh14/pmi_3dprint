# Bootstrap Guide - Từ zip → Bắt đầu vibe coding

> Hướng dẫn step-by-step để go từ "vừa nhận zip" → "Claude Code build feature đầu tiên".

## 📋 Checklist tổng quan

- [ ] **Step 1**: Cài đặt tools cần thiết (1 lần duy nhất)
- [ ] **Step 2**: Setup Supabase project
- [ ] **Step 3**: Extract zip + git init
- [ ] **Step 4**: Paste spec gốc vào `docs/architecture/full-spec.md`
- [ ] **Step 5**: Verify file structure
- [ ] **Step 6**: Mở Claude Code trong VS Code
- [ ] **Step 7**: Scaffold Django + Next.js (qua Claude Code)
- [ ] **Step 8**: Test setup chạy được
- [ ] **Step 9**: Build feature đầu tiên (CRUD Product) qua pipeline đầy đủ

---

## Step 1: Cài đặt tools (1 lần duy nhất)

### macOS / Linux
```bash
# Homebrew (mac) hoặc apt/dnf (linux)
brew install python@3.11 node@20 git docker

# Hoặc dùng pyenv + nvm để manage version

# Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

### Windows
1. Python 3.11+: https://www.python.org/downloads/
2. Node.js 20 LTS: https://nodejs.org/
3. Git: https://git-scm.com/download/win
4. Docker Desktop: https://www.docker.com/products/docker-desktop
5. Windows Terminal (recommended): từ Microsoft Store
6. VS Code: https://code.visualstudio.com
7. Claude Code CLI:
```powershell
npm install -g @anthropic-ai/claude-code
```

### VS Code extensions

Cài qua VS Code Marketplace:
- ✅ Python (Microsoft)
- ✅ Pylance
- ✅ Ruff (charliermarsh)
- ✅ ESLint (Microsoft)
- ✅ Prettier - Code formatter
- ✅ Tailwind CSS IntelliSense
- ✅ GitLens (optional, debug Git dễ)
- ✅ Even Better TOML

### Verify

```bash
python --version      # Python 3.11.x
node --version        # v20.x.x
git --version
docker --version
claude --version      # Claude Code
```

---

## Step 2: Setup Database (chọn 1)

### Option A — Local Postgres Docker (RECOMMENDED for dev)

Không cần làm gì, đã có sẵn trong `docker-compose.yml`. Khi chạy `docker compose up -d` ở Step 8 sẽ tự khởi tạo:
- Postgres 16 với extensions (ltree, pg_trgm, unaccent, ...)
- Redis 7
- MinIO (S3-compatible storage cho STL files)
- Auto-create buckets `design-files` + `media-assets`

✅ Lợi ích: nhanh, offline, isolated, không lo Supabase pause.

Đi tiếp Step 3.

### Option B — Supabase (cho staging/prod, hoặc nếu muốn cloud từ đầu)

1. Đăng ký tài khoản tại https://supabase.com (free)
2. Create new project:
   - **Name**: `3dprint-pim-staging` (hoặc `-prod`)
   - **Database password**: lưu kỹ! (cần cho `.env`)
   - **Region**: `Southeast Asia (Singapore)` cho VN
   - **Pricing**: Free tier (đủ cho staging)
3. Đợi 2-3 phút project khởi tạo
4. Vào **Project Settings → Database**:
   - Copy `Connection string` URI (chọn "Transaction pooler" port 6543)
   - Sẽ dùng cho `DATABASE_URL` trong `.env`
5. Vào **Project Settings → API**:
   - Copy `Project URL`, `anon` key, `service_role` key
6. Vào **Storage** tab:
   - Create bucket `design-files` (private)
   - Create bucket `media-assets` (public)
7. Vào **Database → Extensions**, enable:
   - `ltree`, `pg_trgm`, `unaccent`, `btree_gin`, `uuid-ossp`

💾 **Lưu credentials** vào folder bên ngoài project:

```
~/secrets/3dprint-pim-credentials.txt:
  Supabase URL: https://xxxxx.supabase.co
  Supabase anon key: eyJxxx...
  Supabase service_role key: eyJyyy... ← KHÔNG bao giờ share/commit
  DB password: xxxx
```

### Khuyến nghị

- **Dev daily**: dùng Option A (local Docker) — fast iteration
- **Staging**: tạo Supabase project riêng (Option B) — test production-like trước khi launch
- **Production**: Supabase project riêng nữa (Option B) — separate dữ liệu thật

Hybrid này = best of both worlds. Code Django/Next.js không cần đổi gì, chỉ đổi `.env` per environment.

---

## Step 3: Extract zip + git init

```bash
# Tạo folder projects nếu chưa có
mkdir -p ~/projects
cd ~/projects

# Extract zip
unzip ~/Downloads/3dprint-pim-bootstrap.zip
cd 3dprint-pim

# Git init
git init
git add -A
git commit -m "chore: initial bootstrap from Claude skill bundle"
```

(Optional) Push lên GitHub:
```bash
# Tạo repo private trên https://github.com/new tên "3dprint-pim"
# (KHÔNG check "Initialize with README" vì đã có local)
git remote add origin git@github.com:YOUR_USERNAME/3dprint-pim.git
git branch -M main
git push -u origin main
```

---

## Step 4: Paste spec gốc

File `docs/architecture/full-spec.md` hiện là placeholder. Cần điền nội dung từ artifact gốc đã được Claude research trước đó.

**Cách làm**:
1. Mở conversation gốc với Claude (nơi có artifact research spec)
2. Tìm artifact tên "Product and SKU Management System for 3D Printing Multi-Channel Sales: Technical Specification"
3. Click icon copy của artifact, copy toàn bộ markdown
4. Mở `docs/architecture/full-spec.md` trong VS Code
5. Xóa nội dung placeholder, paste artifact vào
6. Save + commit:
```bash
git add docs/architecture/full-spec.md
git commit -m "docs(architecture): add original full spec"
```

---

## Step 5: Verify file structure

```bash
tree -L 3 -I 'node_modules|__pycache__|.venv'
```

Should see:

```
3dprint-pim/
├── CLAUDE.md
├── README.md
├── BOOTSTRAP_GUIDE.md
├── .gitignore
├── docker-compose.yml
├── .claude/
│   └── skills/
│       ├── ba-spec/
│       ├── code-review/
│       ├── db-schema/
│       ├── django-backend/
│       ├── nextjs-frontend/
│       └── test-generator/
├── docs/
│   ├── README.md
│   ├── product/
│   │   ├── PRD.md
│   │   └── personas.md
│   ├── architecture/
│   │   ├── ARCHITECTURE.md
│   │   ├── business-rules.md
│   │   ├── conventions.md
│   │   ├── full-spec.md          ← Đã paste spec gốc
│   │   ├── glossary.md
│   │   └── tech-stack.md
│   └── features/
│       └── _template/
│           ├── ANALYSIS.md
│           ├── DESIGN.md
│           ├── SPEC.md
│           └── TASKS.md
├── backend/
│   └── .env.example
└── frontend/
    └── .env.example
```

---

## Step 6: Mở Claude Code trong VS Code

```bash
cd ~/projects/3dprint-pim
code .          # Mở VS Code
```

Trong VS Code, mở terminal (`Ctrl+`` ` hoặc `View → Terminal`):

```bash
claude
```

Claude Code sẽ load:
- `CLAUDE.md` (context chính)
- 6 skills trong `.claude/skills/`

**Verify skills loaded**:
```
/skills
```

Should list 6 skills: ba-spec, code-review, db-schema, django-backend, nextjs-frontend, test-generator.

---

## Step 7: Scaffold Django + Next.js

Trong Claude Code session, paste prompt sau:

```
Đọc CLAUDE.md, docs/architecture/ARCHITECTURE.md, docs/architecture/tech-stack.md, 
và docs/architecture/full-spec.md để hiểu context dự án.

Sau đó scaffold:

1. Backend Django:
   - Tạo virtualenv .venv trong backend/
   - Init Django project tên "config" trong backend/
   - Setup pyproject.toml với deps theo tech-stack.md
   - Tạo app `core` đầu tiên với TimestampedModel, SoftDeleteModel, AuditedModel, AuditLog
   - Setup settings split (base/dev/prod/test)
   - Setup Celery integration
   - Setup DRF + JWT + CORS + drf-spectacular
   - Verify: python manage.py check pass, makemigrations dry-run OK

2. Frontend Next.js:
   - npm create next-app frontend với TypeScript + Tailwind + App Router
   - Setup shadcn/ui (npx shadcn-ui@latest init)
   - Install: @tanstack/react-query, @tanstack/react-table, axios, react-hook-form, zod, @hookform/resolvers, sonner, next-intl, zustand
   - Setup folder structure theo ARCHITECTURE.md
   - Create lib/api/client.ts skeleton
   - Verify: npm run dev chạy được, npm run lint pass

QUAN TRỌNG:
- Làm từng phần (BE trước, FE sau), sau mỗi phần STOP và hỏi tôi test
- KHÔNG cài thêm package ngoài list trên trừ khi hỏi tôi trước
- Sau khi xong scaffold, commit: chore(setup): scaffold Django + Next.js
- KHÔNG bắt đầu code feature, chỉ scaffold infrastructure
```

Claude sẽ:
- Scan các docs
- Bắt đầu scaffold theo thứ tự
- Hỏi bạn confirm sau mỗi phần

**Estimate time**: 2-3 giờ (có break giữa các step để test).

---

## Step 8: Test setup

### Khởi động docker services (Postgres + Redis + MinIO)

```bash
cd ~/projects/3dprint-pim
docker compose up -d
docker compose ps      # Should show postgres, redis, minio Up + minio-setup Exited(0)
```

**Verify**:
- Postgres: `docker compose exec postgres psql -U pim_user -d pim_dev -c "SELECT extname FROM pg_extension;"` → list các extensions
- MinIO web console: http://localhost:9001 (login: minioadmin / minioadmin) → thấy buckets `design-files` + `media-assets`

### Backend smoke test
```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
cp .env.example .env
# .env mặc định đã trỏ Block A (local docker) - không cần đổi gì
# Chỉ cần generate JWT_SIGNING_KEY + FIELD_ENCRYPTION_KEY:
python -c "import secrets; print('JWT:', secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print('FIELD:', Fernet.generate_key().decode())"
# Paste vào .env tương ứng

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://localhost:8000/admin → login với superuser → thấy Django admin.

Visit http://localhost:8000/api/schema/swagger-ui/ → thấy Swagger UI từ drf-spectacular.

### Celery worker
```bash
# Terminal mới
cd backend && source .venv/bin/activate
celery -A config worker -l info
# Should show worker connected to Redis, no errors
```

### Frontend smoke test
```bash
# Terminal mới
cd frontend
cp .env.example .env.local
# Mặc định đã trỏ http://localhost:8000/api + MinIO local - không cần đổi

npm run dev
```

Visit http://localhost:3000 → thấy default Next.js page.

✅ Nếu tất cả pass, scaffold done!

```bash
cd ..
git add -A
git commit -m "chore(setup): complete scaffold + smoke tests pass"
```

### Stop services khi không dev

```bash
docker compose down              # Stop, giữ data
docker compose down -v           # Stop + xóa data (reset DB!)
```

---

## Step 9: Build feature đầu tiên - CRUD Product

Trong Claude Code session (tiếp tục hoặc start mới), gõ:

```
Tôi muốn build feature CRUD Product. Đây sẽ là feature đầu tiên để test pipeline đầy đủ.
```

Đây là điểm trigger skill `ba-spec`. Pipeline sẽ chạy:

### Pipeline expected

#### PHA 1: BA Analysis
Claude (ba-spec skill) sẽ hỏi **6 câu** (1 câu/turn):

1. Pain point cụ thể là gì? Persona nào gặp?
2. Bằng chứng (user feedback, observation, đoán)?
3. MVP scope alignment?
4. Effort estimate (BE + FE + test)?
5. Alternatives đã cân nhắc?
6. Success metric đo bằng gì?

Sau khi bạn trả lời, Claude tạo `docs/features/01-product-crud/ANALYSIS.md` với **verdict** 🟢🟡🟠🔴 + reasoning.

**Claude STOP và đợi confirm**.

#### PHA 2: SPEC + DESIGN + TASKS

Sau khi bạn confirm "build now", Claude (ba-spec PHA 2) hỏi thêm 3-5 câu detail:
- User flow chi tiết
- Edge cases
- Permission per role
- API contract gợi ý

Tạo:
- `docs/features/01-product-crud/SPEC.md`
- `docs/features/01-product-crud/DESIGN.md`
- `docs/features/01-product-crud/TASKS.md`

**Claude STOP và đợi review**.

#### PHA 3: Implementation

Sau khi bạn OK specs, Claude (db-schema → django-backend → test-generator → nextjs-frontend) implement theo TASKS.md từng task.

Mỗi task xong → bạn test → commit.

#### PHA 4: Code review

Trước commit cuối, Claude (code-review) check findings theo severity 🔴🟠🟡.

---

## 🎯 Tips cho session đầu tiên

### Time budget
- **Setup (Step 1-6)**: 1-2 giờ
- **Scaffold (Step 7-8)**: 2-3 giờ
- **First feature CRUD Product (Step 9)**: 4-6 giờ (chia 2-3 session)

### Session length
- **Max 2 giờ/session** — sau đó context window đầy, Claude bắt đầu lú
- Hết 2 giờ → kết session với câu thần chú:
  > "Tổng kết những gì đã làm, update `docs/features/01-product-crud/CHANGELOG.md`, và liệt kê 3 tasks tiếp theo trong TASKS.md."

### Khi Claude làm sai
- **Lần 1**: giải thích lại, để Claude sửa
- **Lần 2**: cung cấp thêm context (paste file liên quan, link spec)
- **Lần 3**: `git reset --hard HEAD` về commit trước, mô tả lại từ đầu

KHÔNG để Claude loop fix > 3 lần.

### Khi mô tả bug
❌ "Bị lỗi rồi"
✅ "Tôi click button X, console hiện `[error]`. Expected là Y, thực tế là Z. Tôi đã thử [...]. Hãy debug."

### Commit thường xuyên
- Mỗi task xong → commit
- Mỗi 1-2h → commit
- Không bao giờ uncommitted changes > 2h

---

## 🚨 Troubleshooting

### Claude Code không load skills
- Verify `.claude/skills/` có 6 folders với SKILL.md
- Trong session, gõ `/skills` để list available
- Restart session: exit + `claude` lại

### Database connection fail
- Check `DATABASE_URL` trong `.env`
- Supabase project có thể bị pause sau 7 ngày không activity → vào Supabase Dashboard → "Restore" project
- Test connection: `python manage.py dbshell`

### Skill không trigger
- Check description trong SKILL.md có match keyword bạn dùng không
- Force trigger: "Use skill `ba-spec` to analyze this feature: ..."

### Migration error
- `python manage.py migrate --plan` để xem thứ tự
- `python manage.py showmigrations` để xem trạng thái
- Nếu development DB → có thể `python manage.py migrate app_name zero` để rollback

---

## 📚 Tài liệu tham khảo

- [CLAUDE.md](CLAUDE.md) - Context chính cho Claude Code
- [README.md](README.md) - Project overview
- [docs/README.md](docs/README.md) - Docs index
- [docs/architecture/full-spec.md](docs/architecture/full-spec.md) - Spec gốc
- [Playbook gốc](../vibe-code-project-setup-playbook.md) - Vibe coding methodology

Chúc bạn vibe coding vui vẻ! 🚀
