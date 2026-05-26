---
name: code-review
description: Review code Django backend và Next.js frontend cho dự án quản lý SKU in 3D đa kênh. Use this skill whenever the user mentions "review", "code review", "check code", "audit code", "review PR", "review giúp", "kiểm tra code", "check security", "performance review", or asks to evaluate any code snippet — even casually like "xem code này có ổn không", "PR này", "đánh giá code". Also triggers when reviewing for convention violations, security holes (SQL injection, XSS, IDOR, secret leak), N+1 queries, missing transactions, race conditions, marketplace API mistakes (Shopee HMAC, Tiki 2-axes limit), license violations, and missing test coverage.
---

# Code Review cho dự án 3D Printing PIM

Skill này review code Django + Next.js theo checklist nghiêm ngặt. Output luôn theo format có thể action ngay (severity + line + fix suggestion).

## Khi nào dùng

- User paste code Python/TS/SQL và hỏi review
- User mở PR và muốn checklist
- User nói "kiểm tra xem có lỗ hổng gì không"
- User hỏi "code này có chuẩn convention không"

## Workflow

1. **Đọc kỹ context**: code thuộc layer nào (model/serializer/view/service/component)?
2. **Apply checklist tương ứng**: dưới đây có 6 checklist riêng cho từng loại code
3. **Xếp severity**:
   - 🔴 **Critical** — security hole, data loss risk, money/license violation → block merge
   - 🟠 **Major** — bug tiềm ẩn, performance kém nghiêm trọng → phải fix trước merge
   - 🟡 **Minor** — convention, readability → nên fix nhưng không block
   - 🔵 **Nit** — style, naming → optional
4. **Output format**:

```markdown
## Tổng quan
[1-2 câu đánh giá tổng thể]

## Findings

### 🔴 Critical
1. **[file:line]** — [tên vấn đề]
   - **Vì sao**: [giải thích ngắn]
   - **Fix**: ```[code suggestion]```

### 🟠 Major
...

### 🟡 Minor
...

## Điểm tốt
- [Ghi nhận những phần làm đúng để encourage]

## Verdict
- [ ] Approve as-is
- [x] Request changes (Critical/Major)
- [ ] Block
```

## Checklist 1: Django Models

- [ ] PK là `UUIDField` (cho entity API-exposed) hoặc `BigAutoField` (internal)
- [ ] FK có `on_delete` đúng strategy:
  - `PROTECT` cho master data (Product, Material, Printer, User)
  - `CASCADE` cho child phụ thuộc 100% (BOMLine với BOM)
  - `SET_NULL` (cần `null=True`) cho metadata (created_by)
- [ ] Có `db_table` explicit (không để Django auto-generate)
- [ ] Money fields: `DecimalField(max_digits, decimal_places=2)`, KHÔNG dùng `FloatField`
- [ ] `null=True` + `blank=True` chỉ khi thực sự nullable, không default
- [ ] Soft delete: model có `deleted_at` hoặc kế thừa `SoftDeleteModel`?
- [ ] Audit: model có `created_by/updated_by` hoặc kế thừa `AuditedModel`?
- [ ] Có `__str__()` method
- [ ] `Meta.indexes` cho các field hay filter (status, deleted_at)
- [ ] `Meta.constraints` (CheckConstraint cho range, UniqueConstraint cho composite unique)
- [ ] JSONB fields có `GinIndex`
- [ ] Migration đã chạy `makemigrations` + có file migration?
- [ ] **Đặc thù dự án**: variant có `material`, `material_color`, `size_preset` (5 trục)?
- [ ] **License**: DesignFile có `license_allows_commercial` derived và set trong `save()`?

## Checklist 2: Django Serializers

- [ ] Tách Input vs Output serializer (không reuse 1 cho cả 2)
- [ ] Input serializer KHÔNG có business logic — chỉ validate format/type
- [ ] Validation business rule → ở service, không ở serializer
- [ ] Không gọi `Model.objects.create()` trong `serializer.create()` — delegate sang service
- [ ] Không expose fields nhạy cảm (password, token, secret) trong output
- [ ] `cost_price` chỉ trong serializer dành cho Production Manager
- [ ] DateTime field có timezone awareness
- [ ] `DecimalField` cho money, không `FloatField`
- [ ] Nested serializer dùng `read_only=True` để tránh accidental write
- [ ] `prefetch_related` / `select_related` được dùng ở selector tương ứng?

## Checklist 3: Django Views / ViewSets

- [ ] View thin — không có business logic
- [ ] Permission class đầy đủ (`permission_classes`)
- [ ] Query có `.select_related()` / `.prefetch_related()` chống N+1
- [ ] Không có raw `Model.objects.all()` — đi qua selector
- [ ] Pagination set (không trả full list)
- [ ] Filtering qua `django-filter`, không tự parse query params
- [ ] Custom action có docstring + URL name
- [ ] Không nhét `try/except` rộng → để DRF exception handler xử lý
- [ ] Status code đúng: 201 cho create, 204 cho delete, 202 cho async, 200 cho rest
- [ ] **Đặc thù**: action `publish_to_channel` trả 202 (async via Celery)?

## Checklist 4: Django Services / Selectors

- [ ] Service: keyword-only args `def variant_create(*, user, ...)`
- [ ] Service: trả model instance, không trả ID
- [ ] Service: side effects rõ ràng (param `push_to_channels=False`), không hidden
- [ ] Service: write operation wrap `@transaction.atomic`
- [ ] Service: validate business rule (vd license check trước khi tạo)
- [ ] Service: gọi `audit_log()` sau mỗi state change
- [ ] Selector: chỉ read, không có side effect
- [ ] Selector: trả `QuerySet` cho list, instance cho single
- [ ] Selector: filter permission/visibility ở đây (không ở view)
- [ ] **Race condition**: SKU generation có `select_for_update()` chưa?
- [ ] **Idempotency**: webhook handler check `ProcessedEvent` trước?

## Checklist 5: Django Celery Tasks

- [ ] `@shared_task(bind=True)` để truy cập `self`
- [ ] `autoretry_for` declare exceptions retryable
- [ ] `retry_backoff` + `retry_jitter` để tránh thundering herd
- [ ] `max_retries` hợp lý (3-5)
- [ ] `soft_time_limit` cho task gọi external API
- [ ] Idempotent: check event_id / unique key trước khi process
- [ ] Atomic: DB writes trong `transaction.atomic`
- [ ] Dead letter: persist payload khi exhausted retries
- [ ] Queue routing: đúng queue (shopee_sync vs lazada_sync vs webhooks)
- [ ] Logging: structured với task_id, args

## Checklist 6: Next.js Components

### Client/Server Component split
- [ ] Server Component mặc định, `'use client'` chỉ khi cần state/effect/event
- [ ] Initial data fetch trong Server Component → pass vào Client Component qua `initialData`
- [ ] Không có `useEffect` để fetch data → React Query thay thế
- [ ] Không có `useState` để cache server data → React Query cache

### Data fetching
- [ ] `useQuery` có `queryKey` từ `*Keys.*` helper (consistency cho invalidation)
- [ ] `useMutation` có `onSuccess` invalidate query liên quan
- [ ] Error handling có toast/UI feedback, không silent
- [ ] Loading state có UI (skeleton/spinner)
- [ ] API error map qua `error_code` để hiển thị message tiếng Việt phù hợp

### Forms
- [ ] `react-hook-form` + zod schema (không validate thủ công)
- [ ] Submit button disabled khi `isPending`
- [ ] Error message hiển thị inline (`FormMessage`)
- [ ] zod schema match với DRF serializer (cùng constraints)

### Performance
- [ ] List có `key` đúng (id, không index)
- [ ] Không inline arrow function trong props gây re-render
- [ ] `useMemo` / `useCallback` chỉ khi đo được lợi ích
- [ ] Image dùng `next/image` (lazy load, optimization)

### Security
- [ ] Không dùng `dangerouslySetInnerHTML` với user input
- [ ] Không expose token trong localStorage (dùng httpOnly cookie)
- [ ] Không log sensitive data ra console
- [ ] CSP headers ở `next.config.mjs`

### i18n & accessibility
- [ ] Strings tiếng Việt qua i18n (`useTranslations()`), không hardcode
- [ ] Button có `aria-label` nếu chỉ icon
- [ ] Form field có `<label>` đi cùng

## Security checklist (CROSS-CUTTING)

### Authentication & Authorization
- [ ] 🔴 **IDOR**: query có filter `user/team/owner` chưa? `Variant.objects.filter(product__owner=request.user.team)`
- [ ] 🔴 **Permission**: action có check `has_perm()` không?
- [ ] 🔴 **Role escalation**: user không tự update role mình
- [ ] 🟠 JWT có expiry hợp lý, refresh token rotation

### Injection
- [ ] 🔴 **SQL injection**: không có `.raw()` với f-string user input; dùng parameterized
- [ ] 🔴 **XSS**: React auto-escape (good); cẩn thận `dangerouslySetInnerHTML`
- [ ] 🔴 **Command injection**: không `subprocess.shell=True` với user input
- [ ] 🟠 **Path traversal**: validate filename, không trust user path

### Secrets
- [ ] 🔴 Không hardcode API key / secret trong code
- [ ] 🔴 `.env` không commit
- [ ] 🟠 Marketplace tokens được encrypt at rest (`MarketplaceCredential.access_token_encrypted`)
- [ ] 🟠 Production secrets qua secret manager (AWS Secrets Manager / Vault)

### Webhook security
- [ ] 🔴 Verify HMAC signature trước khi process (Shopee, Lazada)
- [ ] 🔴 Idempotency check qua `event_id`
- [ ] 🟠 Reject webhook quá cũ (> 5 phút)

### File upload
- [ ] 🔴 Validate MIME + magic bytes, không chỉ extension
- [ ] 🔴 Scan virus (ClamAV) cho file > 10MB
- [ ] 🟠 Max file size enforce ở cả FE + BE
- [ ] 🟠 Store ngoài web root, serve qua signed URL

### Marketplace-specific
- [ ] 🔴 Shopee HMAC: dùng `hmac.compare_digest()`, không `==`
- [ ] 🔴 Tiki: check `len(option_attributes) <= 2` trước khi push
- [ ] 🟠 Safety stock buffer 5-10% để chống overselling
- [ ] 🟠 Stock sync timeout < 30s

### License compliance
- [ ] 🔴 Block publish variant nếu `license_allows_commercial = False`
- [ ] 🟠 Audit log khi đổi license_type của design_file
- [ ] 🟠 Hiển thị credit (attribution) nếu license requires

## Performance checklist

### Database
- [ ] 🟠 N+1: query có `.select_related()` / `.prefetch_related()`?
- [ ] 🟠 Filter trên indexed column? Có `EXPLAIN ANALYZE` chưa?
- [ ] 🟠 Pagination có dùng cursor-based cho list lớn (orders, audit_logs)?
- [ ] 🟡 `bulk_create()` cho insert nhiều rows, không loop save
- [ ] 🟡 `bulk_update()` cho update nhiều, không loop save
- [ ] 🟡 `only()` / `defer()` khi list view chỉ cần vài fields

### API
- [ ] 🟠 Response size: variant list không trả full BOM (lazy load)
- [ ] 🟠 Async cho task chậm (push marketplace) qua Celery
- [ ] 🟡 Cache với Redis cho data ít thay đổi (category tree, attribute_definitions)

### Frontend
- [ ] 🟠 Bundle size: tránh import full lodash, import từng function
- [ ] 🟡 Lazy load route components
- [ ] 🟡 Image `next/image` với appropriate `sizes`
- [ ] 🟡 React Query `staleTime` set hợp lý (60s cho catalog, 0 cho stock)

## Output ví dụ

```markdown
## Tổng quan
Code service `variant_create` đã tách logic ra khỏi view tốt, nhưng có 1 race condition nghiêm trọng khi generate SKU và missing audit log.

## Findings

### 🔴 Critical

1. **apps/skus/services/variant.py:23** — Race condition khi generate SKU
   - **Vì sao**: 2 transaction đồng thời có thể gen cùng 1 sequence number → SKU collision (vi phạm BR-001)
   - **Fix**: thêm `select_for_update()` lock trên Product:
     ```python
     product = Product.objects.select_for_update().get(id=product_id)
     ```

2. **apps/skus/services/variant.py:45** — License check thiếu khi promote variant từ draft sang active
   - **Vì sao**: BR-003 yêu cầu block active nếu license CC BY-NC
   - **Fix**: 
     ```python
     if status == 'active' and design_file and not design_file.license_allows_commercial:
         raise LicenseCommercialBlockError(...)
     ```

### 🟠 Major

3. **apps/skus/services/variant.py:52** — Missing audit log
   - **Vì sao**: BR-009 yêu cầu audit mọi state change của variant
   - **Fix**: thêm `audit_log(actor=user, action='variant.created', entity=variant, diff={...})` sau khi tạo

### 🟡 Minor

4. **apps/skus/services/variant.py:15** — Hàm thiếu type hint return value
   - **Fix**: `def variant_create(...) -> Variant:`

## Điểm tốt
- ✅ `@transaction.atomic` decorator đúng vị trí
- ✅ Keyword-only args theo HackSoft styleguide
- ✅ Tách validate license sang `design_file_check_license_for_commercial` reusable

## Verdict
- [x] Request changes (2 Critical, 1 Major cần fix)
```

## Anti-patterns common (red flags)

❌ `except: pass` hoặc `except Exception: pass` → mask bugs  
❌ `print()` thay vì `logger` trong production code  
❌ `TODO` / `FIXME` không có ticket reference  
❌ Magic number không có constant (vd `if x > 50:`)  
❌ Commit code có `console.log` / `breakpoint()`  
❌ Test bị skip (`@pytest.mark.skip`) không có lý do  
❌ Migration "fake" (`--fake`) thay vì proper migration  
❌ Hardcode environment-specific (URL, path)  
❌ Comment trùng với code (`i = i + 1  # increment i`)  
❌ Function > 50 dòng — cần tách
