# BA Templates

## 1. Epic / Feature Spec Template

```markdown
# Epic: [Tên epic]

## Overview
**Module**: [Catalog | SKU | POC | Channel Sync | ...]
**Owner**: [PM/BA name]
**Target release**: [Sprint/Quarter]
**Status**: Draft | In Review | Approved | In Dev | Done

## Business context
[Tại sao cần feature này? Pain point hiện tại? Business value?]

## Goals & Non-goals
**Goals**:
- G1: ...
- G2: ...

**Non-goals** (rõ ràng KHÔNG làm trong scope này):
- NG1: ...

## Success metrics
- Metric 1: [đo gì, target bao nhiêu, đo bằng cách nào]
- Metric 2: ...

## User personas affected
- [Role A]: [họ tương tác với feature thế nào]
- [Role B]: ...

## User journeys (high level)
1. [Persona] → [Step 1] → [Step 2] → [Outcome]

## Stories breakdown
| ID | Title | Priority | Estimate | Dependencies |
|----|-------|----------|----------|--------------|
| US-001 | ... | P0 | M | - |
| US-002 | ... | P1 | S | US-001 |

## Out of scope (deferred)
- ...

## Open questions
- [ ] Q1: ...
- [ ] Q2: ...

## References
- Spec doc: [link]
- Design: [Figma link]
- Related epic: ...
```

## 2. Use Case Detail Template

```markdown
# UC-XXX: [Tên use case]

**Primary actor**: [Role]
**Stakeholders**: [list các bên liên quan]
**Preconditions**: 
- [Điều kiện trước khi UC bắt đầu]

**Trigger**: [Event khởi đầu UC]

## Main Flow (Happy path)
1. Actor [does X]
2. System [responds Y]
3. Actor [does Z]
4. System [validates và saves]
5. System [returns confirmation]
6. UC kết thúc thành công

## Alternative Flows
### AF-1: [Tên alternative]
**Branch from**: Step N in main flow
1. Thay vì step N, actor [does W]
2. System [responds differently]
3. Quay lại main flow step M (hoặc kết thúc)

### AF-2: ...

## Exception Flows
### EF-1: [Validation fail]
**Branch from**: Step N
1. Hệ thống phát hiện [error condition]
2. System hiển thị error "..."
3. Actor có thể retry hoặc cancel
4. UC kết thúc (success/fail)

### EF-2: [External API timeout]
...

## Postconditions (success)
- [State của system sau khi UC thành công]

## Postconditions (failure)
- [State nếu UC fail]
```

## 3. Story Mapping Template

```
Backbone (user journeys, đọc trái → phải):
[Discover] → [Setup] → [Use daily] → [Optimize] → [Archive]

Cho mỗi step ở backbone, list stories từ MVP đến nice-to-have:

[Discover]
  MVP: US-001 Browse products
  P1:  US-010 Search with filters
  P2:  US-020 AI recommendations

[Setup]
  MVP: US-002 Create first SKU
  P1:  US-011 Bulk import CSV
  P2:  US-021 Import from competitor

...
```

## 4. Decision Table (cho complex business logic)

Khi rule có nhiều điều kiện, dùng decision table thay vì if-else lồng nhau.

Ví dụ: "Có cho phép publish variant lên kênh không?"

| # | License allows commercial | Has STL file | Has GLB preview | Stock > 0 | Result |
|---|---|---|---|---|---|
| 1 | Y | Y | Y | Y | ✅ Allow publish |
| 2 | N | * | * | * | ❌ Block: License violation |
| 3 | Y | N | * | * | ❌ Block: No design file |
| 4 | Y | Y | N | * | ⚠️ Warn: Generate GLB first |
| 5 | Y | Y | Y | N | ⚠️ Warn: Out of stock, publish as draft only |

(* = any/don't care)

## 5. API Contract Template (cho AC)

```yaml
endpoint: POST /api/v1/products/
auth: Bearer token (role: catalog_manager+)
request:
  name: string (1-200 chars, required)
  category_id: uuid (required, must exist)
  attributes: object (optional, JSON)
  variants:
    - axes: { material, color, size, ... }
      base_price: number (>= 0)
      cost_price: number (>= 0)
response:
  201:
    id: uuid
    sku_root: string
    variants: [...]
  400:
    error_code: VALIDATION_ERROR | LICENSE_BLOCK | SKU_CONFLICT
    message: string
    details: object
  403: PERMISSION_DENIED
  500: INTERNAL_ERROR
```

## 6. Risk & Impact Matrix

| Risk | Likelihood (L/M/H) | Impact (L/M/H) | Mitigation |
|------|--------------------|-----------------|------------|
| Marketplace API breaking change | H | H | Version connector, daily smoke test trên sandbox |
| Overselling do sync chậm | M | H | Safety stock 5-10%, webhook real-time |
| Variant explosion | H | M | UI warning khi > 50 variants, quarterly audit |
| File STL bị nhiễm virus | L | H | ClamAV scan khi upload, sandbox MIME check |
