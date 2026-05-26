---
name: ba-spec
description: Phân tích yêu cầu nghiệp vụ và viết tài liệu BA cho dự án quản lý sản phẩm/SKU in 3D đa kênh. Use this skill whenever the user mentions "user story", "acceptance criteria", "use case", "BA", "spec", "yêu cầu nghiệp vụ", "tài liệu phân tích", "refine spec", "user flow", "epic", "story mapping" — even casually like "viết story cho tính năng X" or "làm spec cho module Y" or "phân tích yêu cầu". Also triggers for breaking down features into tickets, writing acceptance criteria in Given-When-Then format, identifying edge cases, creating user personas, and refining vague product requirements into dev-ready specs.
---

# BA Spec Writer cho dự án 3D Printing PIM

Skill này giúp viết tài liệu phân tích nghiệp vụ (Business Analysis) cho hệ thống quản lý sản phẩm + SKU + đa kênh dành cho doanh nghiệp in 3D. Output luôn ở định dạng dev có thể implement được ngay.

## Khi nào dùng skill này

- User nói "viết user story cho ...", "làm spec cho tính năng ...", "phân tích yêu cầu ..."
- User paste mô tả tính năng mơ hồ và muốn refine thành ticket dev được
- User muốn break epic thành stories, hoặc story thành tasks
- User cần acceptance criteria, edge case checklist, hoặc business rule documentation

## 🚦 PHA 1: GATE (BẮT BUỘC - KHÔNG BYPASS)

**Khi user request 1 feature mới**, KHÔNG vội viết spec. Phải gate qua 2 bước:

### Step 1.1 — Đặt 6 câu hỏi (max 1 câu/turn, không bombard)

1. **Vấn đề**: Pain point cụ thể đang giải quyết là gì? Persona nào gặp pain này?
2. **Bằng chứng**: User đã yêu cầu rõ ràng (vd anh Hùng nói "tôi mất 2h/tuần làm việc này")? Hay đoán?
3. **MVP alignment**: Có nằm trong scope MVP hiện tại (xem `docs/product/PRD.md`)? Nếu out of scope → defer.
4. **Cost vs Value**: Estimate effort (S/M/L/XL) vs impact (reach × importance × confidence).
5. **Alternatives**: Có cách nào đơn giản hơn không (vd dùng Excel/script thay vì code UI)?
6. **Success metric**: Đo bằng gì? Bao lâu sau launch evaluate?

### Step 1.2 — Tạo `docs/features/NN-name/ANALYSIS.md` với 1 trong 4 verdicts

```markdown
# Feature Analysis: [Name]

## Summary
[1-liner]

## Problem Statement
[Pain point + persona]

## MVP Alignment
- [ ] In MVP scope (xem PRD.md)
- [ ] Aligns với primary goal
- [ ] Không conflict với "Out of Scope"

## Impact
- **Reach**: bao nhiêu % users (roles nào) hưởng lợi
- **Importance**: Critical / Nice-to-have / Cosmetic
- **Confidence**: High / Medium / Low (dựa trên evidence)

## Effort estimate
- Backend: X giờ
- Frontend: Y giờ
- Test: Z giờ
- Total: T giờ

## Alternatives considered
- Option A (rejected: ...)
- Option B (rejected: ...)

## Risks
- Risk 1

## Recommendation
🟢 BUILD NOW — đúng MVP, impact cao, effort hợp lý
🟡 BUILD LATER — đúng nhưng không phải priority này sprint
🟠 SIMPLIFY — scope quá to, đề xuất MVP nhỏ hơn
🔴 DON'T BUILD — out of MVP hoặc cost > value

**Reasoning**: [Giải thích quyết định]

## Next steps
→ [Nếu 🟢: tiến vào PHA 2 sau khi user confirm]
→ [Nếu 🟡: add vào backlog]
→ [Nếu 🟠: đề xuất scope nhỏ hơn]
→ [Nếu 🔴: explain lý do, đề xuất alternative]
```

### Step 1.3 — STOP và đợi user

Sau khi tạo ANALYSIS.md:
- **KHÔNG tự động viết SPEC.md/DESIGN.md/TASKS.md**
- Show verdict + reasoning cho user
- Đợi user confirm: "OK build now" hoặc "đổi sang BUILD LATER" hoặc "rethink"
- CHỈ KHI user explicit "build now" / "tiến hành" → vào PHA 2

**Anti-pattern**: tự động vào PHA 2 vì "nghe có vẻ đơn giản". Gate tồn tại để tránh feature creep.

## 🚦 PHA 2: DETAIL SPEC (sau khi user confirm 🟢 BUILD NOW)

### Step 2.1 — Đọc lại ANALYSIS.md và hỏi 3-5 câu chi tiết

- User flow end-to-end (step 1, 2, 3...)?
- Edge cases nào cần handle?
- Acceptance criteria — đo bằng cách nào?
- Permission: role nào được làm gì?
- Dependencies: cần feature/module nào sẵn trước?

### Step 2.2 — Tạo 3 files trong `docs/features/NN-name/`

**SPEC.md** — What & Why
- User flow chi tiết
- Acceptance criteria (Given-When-Then)
- Edge cases checklist
- Out of scope (explicit)
- Dependencies

**DESIGN.md** — How (technical)
- Component breakdown (BE: models, services, viewset; FE: pages, components)
- Data flow diagram
- Files to create/modify
- Technical decisions (chose X over Y because Z)
- API contract gợi ý

**TASKS.md** — Breakdown thành tasks 1-2h
- Task 1: [Name] (Xh) — Deliverable: [test-able outcome]
- Task 2: ...

### Step 2.3 — STOP lần 2 và đợi user review

Show 3 files đã tạo. Đợi user confirm trước khi handoff sang `django-backend` / `nextjs-frontend` skills implement.

## Loại tài liệu khác (khi user CHỦ ĐỘNG yêu cầu, không phải feature mới)

Nếu user yêu cầu các loại khác (không phải feature mới), bypass gate:
- **User story đơn lẻ** — viết theo format ở section "Format output mặc định"
- **Use case detail** — xem `references/templates.md`
- **Acceptance Criteria** cho story đã có
- **Business rules** + decision table

### Áp dụng context dự án
Luôn nhớ context của dự án này:
- **Domain**: in 3D, bán đa kênh (Shopee/Lazada/Tiki/POS)
- **Roles chính**: Catalog Manager, Production Manager, Channel Operator, Designer, Cashier, Super Admin
- **Modules chính**: Catalog, SKU/Variants, Design Files, Ideas, POC/Costing, Materials/BOM, Printers, Channel Sync, POS
- **Đặc thù 3D**: variant nhiều trục (material × color × size × layer res × infill), file STL/GCODE, license CC, BOM theo gram filament, máy in tương thích
- **Constraint đa kênh**: Tiki giới hạn 2 option attributes, mỗi sàn có SKU mapping riêng

### Templates

Xem `references/templates.md` để lấy template chi tiết cho từng loại tài liệu.

## Format output mặc định

### User Story format
```markdown
## US-XXX: [Tên ngắn gọn]

**Story**: As a [role], I want to [action], so that [benefit].

**Priority**: P0/P1/P2/P3  
**Effort estimate**: XS/S/M/L/XL  
**Module**: [Catalog | SKU | POC | Channel Sync | ...]  
**Dependencies**: US-YYY, US-ZZZ

### Mô tả chi tiết
[Bối cảnh nghiệp vụ, why behind the story]

### Acceptance Criteria (Given-When-Then)
1. **Given** [precondition]  
   **When** [action]  
   **Then** [expected result]
2. ...

### Edge cases cần handle
- [ ] Trường hợp 1
- [ ] Trường hợp 2

### Business rules áp dụng
- BR-001: ...

### UI/UX notes
- [Mô tả màn hình hoặc reference design]

### API contract gợi ý
```
POST /api/products/
Request: {...}
Response: {...}
```

### Test scenarios
1. Happy path: ...
2. Error case: ...
3. Edge case: ...

### Definition of Done
- [ ] Code implemented + reviewed
- [ ] Unit test coverage >= 80%
- [ ] Integration test pass
- [ ] API doc updated (OpenAPI)
- [ ] Tested trong sandbox marketplace nếu liên quan sync
- [ ] PM/BA sign-off
```

## Nguyên tắc viết AC

**LUÔN dùng Given-When-Then** (Gherkin-style). Không viết AC dạng bullet "phải làm X" mơ hồ.

**Bad**:
- "User có thể tạo sản phẩm với nhiều biến thể"

**Good**:
```
Given user là Catalog Manager đã đăng nhập
And user đang ở màn hình "Create Product"
When user nhập tên sản phẩm "Dragon Figure"
And user thêm 3 màu (red, blue, green) và 2 size (S, M)
And user click "Generate All Variants"
Then hệ thống tạo ra 6 variants với SKU auto-generated
And mỗi SKU tuân theo pattern [CAT3]-[PROD]-[MAT]-[COLOR]-[SIZE]-[NN]
And user thấy preview table 6 dòng trước khi save
```

## Edge case checklist mặc định cho dự án 3D printing

Mỗi feature mới, **bắt buộc** review các edge case sau (skip nếu không liên quan):

### Variant / SKU
- [ ] SKU trùng khi auto-generate (sequence collision)
- [ ] Variant explosion: tạo > 100 variants 1 lần
- [ ] Đổi attribute axis sau khi đã có variants (vd thêm "layer resolution" sau khi đã có 30 variants)
- [ ] Variant không có file STL gắn vào
- [ ] Variant có nhiều file STL versions, không rõ version nào active

### File thiết kế
- [ ] Upload file > 500MB
- [ ] Upload file không phải format hỗ trợ (vd .blend)
- [ ] File STL corrupt (parse fail)
- [ ] License = CC BY-NC nhưng staff cố publish variant
- [ ] File từ Thingiverse nhưng không có source_url
- [ ] Đổi license của file đang được bán

### POC & Costing
- [ ] Giá nguyên liệu thay đổi giữa các POC version
- [ ] POC chưa có data filament_used (worker quên ghi)
- [ ] Máy in dùng cho POC bị retired
- [ ] Cost cao hơn giá bán hiện tại (margin âm)

### Đa kênh
- [ ] Push lên kênh nhưng kênh trả lỗi (API timeout, validation fail)
- [ ] SKU trên kênh đã bị buyer khác đặt trước khi sync stock
- [ ] Webhook trễ > 5 phút (eventual consistency window)
- [ ] Tiki từ chối vì > 2 option attributes
- [ ] Lazada yêu cầu category attributes bắt buộc chưa map
- [ ] Token Shopee hết hạn giữa job

### POS offline
- [ ] Mất mạng khi đang scan barcode
- [ ] Conflict khi 2 POS bán cùng SKU cuối cùng
- [ ] Tem in lỗi (máy hết giấy / sai khổ)

### General
- [ ] Concurrent edit (2 users cùng update 1 variant)
- [ ] Soft delete vs hard delete
- [ ] Permission denied (role không đủ)
- [ ] Audit log mọi state change
- [ ] i18n (tên sản phẩm tiếng Việt có dấu)

## Business rules library

Mã hóa rules dạng `BR-XXX` để reference. Ví dụ rules đã có sẵn từ spec:

- **BR-001**: SKU phải unique trong toàn hệ thống, không phân biệt case.
- **BR-002**: SKU pattern bắt buộc `[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]`, độ dài 12–24 ký tự.
- **BR-003**: Variant không thể chuyển sang status `active` nếu `design_file.license_allows_commercial = false`.
- **BR-004**: Khi push variant lên Tiki, nếu số option_attributes > 2 → block + suggest merge axes.
- **BR-005**: Cost POC = material + electricity + depreciation + labor + failure_buffer.
- **BR-006**: Stock sync giữa các kênh phải hoàn thành trong 30s từ khi master stock change.
- **BR-007**: Safety stock buffer 5–10% mỗi kênh để chống overselling.
- **BR-008**: File STL > 100MB phải có GLB preview generated trước khi gắn vào variant active.
- **BR-009**: Audit log mọi thay đổi: license_type, price, stock, variant status.
- **BR-010**: Internal barcode dùng EAN-13 prefix 020–029; GS1 prefix 893 chỉ khi đã đăng ký GS1 VN.

Khi viết spec mới phát hiện rule mới → append vào danh sách này.

## Reference files

- `references/templates.md` — Template chi tiết cho Epic, Use Case, Story Mapping, Decision Table
- `references/roles.md` — Mô tả 6 roles + permissions matrix
- `references/glossary.md` — Thuật ngữ 3D printing + e-commerce VN

## Anti-patterns cần tránh

❌ **AC mơ hồ**: "system phải nhanh" → ✅ "API response < 500ms p95"  
❌ **Story quá lớn**: "Manage SKU" → ✅ split thành CRUD + bulk import + variant matrix + ...  
❌ **Mix logic vào AC**: viết SQL/code trong AC → ✅ AC chỉ describe behavior, để dev tự design  
❌ **Bỏ qua role**: chỉ nói "user" → ✅ chỉ rõ Catalog Manager / Production Manager / ...  
❌ **Không có error case**: chỉ happy path → ✅ ít nhất 2 error AC cho mỗi story  
❌ **Hardcode UI vào spec**: "button màu xanh ở góc phải" → ✅ "primary action button, position theo design system"
