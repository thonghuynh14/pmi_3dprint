# 3D Printing PIM

Hệ thống quản lý sản phẩm và SKU cho doanh nghiệp in 3D, bán đa kênh (Shopee, Lazada, Tiki, POS offline).

## Stack

- **Backend**: Django 5 + DRF + PostgreSQL 16 + Celery + Redis
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- **Database & Storage**: Hybrid pattern
  - **Dev**: Local Postgres + MinIO trong Docker
  - **Staging/Prod**: Supabase Postgres + Supabase Storage
- **Auth**: Django (không dùng Supabase Auth)

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Docker + Docker Compose (cho Postgres, Redis, MinIO local)
- (Optional) Supabase project cho staging/prod ([signup](https://supabase.com))
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`

### Setup lần đầu

```bash
# 1. Clone repo
git clone <repo-url> 3dprint-pim
cd 3dprint-pim

# 2. Start docker services (Postgres + Redis + MinIO)
docker compose up -d

# 3. Backend
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env          # Default trỏ tới docker local
# Generate JWT_SIGNING_KEY + FIELD_ENCRYPTION_KEY, paste vào .env
python manage.py migrate
python manage.py createsuperuser

# 4. Frontend
cd ../frontend
npm install
cp .env.example .env.local    # Default trỏ http://localhost:8000/api
```

### Chạy dev

```bash
# Terminal 1: backend
cd backend && source .venv/bin/activate && python manage.py runserver

# Terminal 2: celery worker
cd backend && source .venv/bin/activate && celery -A config worker -l info

# Terminal 3: frontend
cd frontend && npm run dev

# Truy cập http://localhost:3000
```

## Làm việc với Claude Code

### Mở session

```bash
cd 3dprint-pim
code .        # Mở VS Code
# Trong VS Code terminal:
claude
```

Claude tự load [CLAUDE.md](CLAUDE.md) + skills trong [.claude/skills/](.claude/skills/).

### Workflow thêm feature

1. **User**: "Tôi muốn thêm tính năng [X]"
2. **Claude (ba-spec skill)**: hỏi 6 câu phân tích → tạo `docs/features/NN-name/ANALYSIS.md` với verdict 🟢🟡🟠🔴 → **STOP**
3. **User**: review verdict, confirm "build now" hoặc "rethink"
4. **Claude (ba-spec skill)**: hỏi 3-5 câu detail → tạo `SPEC.md` + `DESIGN.md` + `TASKS.md` → **STOP**
5. **User**: review specs
6. **Claude (db-schema / django-backend / nextjs-frontend / test-generator skills)**: implement theo TASKS.md
7. **Claude (code-review skill)**: review trước commit
8. **User**: `git commit` (Conventional Commits)

## Docs

- [docs/product/PRD.md](docs/product/PRD.md) — Product Requirements
- [docs/product/personas.md](docs/product/personas.md) — 6 roles + persona profiles
- [docs/architecture/full-spec.md](docs/architecture/full-spec.md) — ★ Spec gốc đầy đủ
- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) — Folder structure + decisions
- [docs/architecture/tech-stack.md](docs/architecture/tech-stack.md) — Tech rationale
- [docs/architecture/business-rules.md](docs/architecture/business-rules.md) — BR-001 → BR-010
- [docs/architecture/conventions.md](docs/architecture/conventions.md) — Coding conventions
- [docs/architecture/glossary.md](docs/architecture/glossary.md) — 3D printing + e-commerce terms

## Skills

| Skill | Mô tả |
|-------|-------|
| [ba-spec](.claude/skills/ba-spec/) | Phân tích nghiệp vụ + viết SPEC/DESIGN/TASKS (gate 🟢🟡🟠🔴) |
| [db-schema](.claude/skills/db-schema/) | Thiết kế PostgreSQL schema + Django models + migrations |
| [django-backend](.claude/skills/django-backend/) | Sinh code BE: services, viewsets, serializers, Celery |
| [nextjs-frontend](.claude/skills/nextjs-frontend/) | Sinh code FE: pages, components, hooks, forms |
| [code-review](.claude/skills/code-review/) | Review code BE/FE với checklist Critical/Major/Minor |
| [test-generator](.claude/skills/test-generator/) | Sinh tests (pytest + factory_boy / Vitest / Playwright) |

## Status

Xem [CLAUDE.md - Status hiện tại](CLAUDE.md#-status-hiện-tại).

## License

Proprietary - Internal use only.
