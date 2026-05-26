# Tasks: [Feature Name]

> Breakdown thành tasks 1-2h. Mỗi task có **deliverable test-able**.

## Status legend
- ⬜ Not started
- 🟡 In progress
- ✅ Done
- ⏸️ Blocked

## Summary
- **Total estimated**: X hours
- **Started**: YYYY-MM-DD
- **Target done**: YYYY-MM-DD

---

## Phase 1: Backend foundation

### Task 1.1: Create models + migration ⬜
**Estimate**: 1.5h
**Deliverable**: `python manage.py migrate` chạy thành công, `python manage.py shell` import được model

**Steps**:
1. Create `apps/[app]/models/[model].py` với fields
2. Add constraints (CheckConstraint, UniqueConstraint)
3. Add indexes (GinIndex cho JSONB, partial index nếu cần)
4. `python manage.py makemigrations`
5. Review migration file, edit nếu cần (RunPython cho data migration)
6. `python manage.py migrate`
7. Test trong shell

**Trigger skills**: `db-schema`

---

### Task 1.2: Create selectors + services ⬜
**Estimate**: 2h
**Deliverable**: Service functions có docstring + type hints, có thể call từ shell

**Steps**:
1. Create `apps/[app]/selectors/[name].py` với functions read
2. Create `apps/[app]/services/[name].py` với functions write
3. Validate business rules (BR-XXX) trong service
4. Wrap `@transaction.atomic` cho write
5. Add `audit_log()` calls
6. Add exception classes trong `apps/[app]/exceptions.py`

**Trigger skills**: `django-backend`

---

### Task 1.3: Create serializers + viewset + URLs ⬜
**Estimate**: 1.5h
**Deliverable**: Endpoints accessible qua curl/Postman với valid auth

**Steps**:
1. Create input + output serializers (separate)
2. Create ViewSet (thin, delegate to service)
3. Add permissions
4. Register URLs trong `apps/[app]/urls.py`
5. Include trong `config/urls.py`
6. Test bằng curl với valid + invalid input

**Trigger skills**: `django-backend`

---

### Task 1.4: Backend tests ⬜
**Estimate**: 2h
**Deliverable**: `pytest apps/[app]` pass với coverage > 80%

**Steps**:
1. Create factories trong `tests/factories.py`
2. Add conftest fixtures
3. Unit tests cho service (happy path + business rule + edge)
4. Integration tests cho API endpoints
5. Parametrized tests cho enums
6. Test concurrent (race condition)
7. Run `pytest --cov=apps.[app]` verify coverage

**Trigger skills**: `test-generator`

---

## Phase 2: Frontend

### Task 2.1: API client + types ⬜
**Estimate**: 1h
**Deliverable**: `lib/api/[resource].ts` + types compile clean

**Steps**:
1. Generate types từ DRF OpenAPI spec (or define manual)
2. Create `lib/api/[resource].ts` với CRUD functions
3. Create `lib/schemas/[resource].ts` zod schemas
4. Create `lib/hooks/use-[resource].ts` React Query hooks

**Trigger skills**: `nextjs-frontend`

---

### Task 2.2: List page (Server Component) ⬜
**Estimate**: 1.5h
**Deliverable**: `/admin/[resource]` shows data table

**Steps**:
1. Create `app/(admin)/[resource]/page.tsx` (server component)
2. Initial data fetch server-side
3. Create `_components/columns.tsx` cho TanStack Table
4. Create `_components/[resource]-list-client.tsx` (client component) với DataTable
5. Add filters + pagination

**Trigger skills**: `nextjs-frontend`

---

### Task 2.3: Create form ⬜
**Estimate**: 2h
**Deliverable**: Có thể tạo record từ UI

**Steps**:
1. Create `components/[domain]/[resource]-create-form.tsx`
2. react-hook-form + zodResolver
3. Field components (Input, Select, etc. from shadcn)
4. useMutation với optimistic update + error handling
5. Toast feedback

**Trigger skills**: `nextjs-frontend`

---

### Task 2.4: Detail + Edit page ⬜
**Estimate**: 1.5h
**Deliverable**: `/admin/[resource]/[id]` shows detail + edit form

---

### Task 2.5: Frontend tests ⬜
**Estimate**: 1.5h
**Deliverable**: `npm test` pass

**Steps**:
1. Vitest unit cho hooks
2. RTL component tests
3. MSW handlers cho mock API
4. Playwright e2e cho 1 happy path

**Trigger skills**: `test-generator`

---

## Phase 3: Polish

### Task 3.1: Manual QA ⬜
**Estimate**: 0.5h
**Deliverable**: Checklist QA pass

**Checklist**:
- [ ] Happy path từ start → end
- [ ] Error message hiển thị đúng (validation, network)
- [ ] Permission: role không đủ thấy 403
- [ ] Responsive mobile + desktop
- [ ] Tiếng Việt có dấu hiển thị đúng
- [ ] Audit log entry created
- [ ] Performance < 500ms response time

---

### Task 3.2: Code review ⬜
**Estimate**: 0.5h

**Trigger skills**: `code-review`

---

### Task 3.3: Documentation update ⬜
**Estimate**: 0.5h

**Steps**:
1. Update `docs/features/NN-name/CHANGELOG.md`
2. Update API docs (drf-spectacular auto)
3. Add to `docs/README.md` features list if needed

---

## Notes

- [Note 1]
- [Note 2]

## Blockers / Open questions

- [ ] Q1: ...
- [ ] Q2: ...

---

*Created by skill: `ba-spec` | Date: YYYY-MM-DD*
