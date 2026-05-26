# Docs Index

## Product

- [PRD.md](product/PRD.md) — Product Requirements Document (1-2 trang ngắn gọn)
- [personas.md](product/personas.md) — 6 roles + persona profiles chi tiết

## Architecture

- [full-spec.md](architecture/full-spec.md) — ★ **SPEC GỐC ĐẦY ĐỦ** (single source of truth)
- [ARCHITECTURE.md](architecture/ARCHITECTURE.md) — High-level architecture + folder structure
- [tech-stack.md](architecture/tech-stack.md) — Tech decisions + alternatives rejected
- [conventions.md](architecture/conventions.md) — Coding conventions (commit, naming, style)
- [business-rules.md](architecture/business-rules.md) — BR-001 → BR-010
- [glossary.md](architecture/glossary.md) — 3D printing + e-commerce + license terms

## Features

Mỗi feature có folder riêng dạng `NN-feature-name/` với 4 files:

- `ANALYSIS.md` — Quyết định có làm không (output từ skill `ba-spec` PHA 1)
- `SPEC.md` — What & Why (output từ skill `ba-spec` PHA 2)
- `DESIGN.md` — How technical (output từ skill `ba-spec` PHA 2)
- `TASKS.md` — Breakdown tasks 1-2h (output từ skill `ba-spec` PHA 2)

Template: [_template/](features/_template/)

### Features đã làm

(Chưa có. Feature đầu tiên dự kiến: `01-product-crud`)

## Workflow

Xem [Workflow trong README](../README.md#workflow-thêm-feature) hoặc [CLAUDE.md](../CLAUDE.md#-quy-trình-thêm-feature-mới-bắt-buộc---không-bypass).
