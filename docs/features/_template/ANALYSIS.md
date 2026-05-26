# Feature Analysis: [Feature Name]

> Output từ skill `ba-spec` PHA 1. Mục đích: gate trước khi build.

## Summary
[1-liner mô tả feature]

## Problem Statement

**Pain point**: [User đang gặp vấn đề gì cụ thể?]

**Evidence**: [Bằng chứng — user đã yêu cầu? Quan sát? Đoán?]

**Persona impacted**: [Catalog Manager / Production Manager / Channel Operator / Designer / Cashier / Super Admin]

## MVP Alignment

- [ ] In current MVP scope (xem [PRD §4.1](../../product/PRD.md))
- [ ] Aligns với primary goal (giảm thời gian idea → live channel)
- [ ] Không conflict với "Out of Scope" trong PRD

## Impact

- **Reach**: X% of staff / X requests/week / X transactions affected
- **Importance**: Critical (block business) / High (significant productivity) / Medium / Low (cosmetic)
- **Confidence**: High (clear evidence) / Medium / Low (assumption)

## Effort estimate

| Component | Hours |
|---|---|
| BE (models, services, viewsets) | X |
| FE (pages, components, forms) | X |
| Test (unit + integration + e2e) | X |
| DB migration | X |
| Total | **X giờ** |

## Alternatives considered

- **Option A**: [mô tả] — Rejected because [reason]
- **Option B**: [mô tả] — Rejected because [reason]

## Risks

- **Risk 1**: [description] — Mitigation: [...]
- **Risk 2**: ...

## Recommendation

🟢 **BUILD NOW** — Đúng MVP, impact cao, effort hợp lý
🟡 **BUILD LATER** — Đúng MVP nhưng không phải priority sprint này
🟠 **SIMPLIFY** — Scope quá to, đề xuất MVP nhỏ hơn: [...]
🔴 **DON'T BUILD** — Out of MVP / cost > value

**Reasoning**: [Giải thích quyết định 2-3 câu]

## Next steps

→ [Nếu 🟢: tiến vào PHA 2 - viết SPEC/DESIGN/TASKS sau khi user confirm]
→ [Nếu 🟡: add vào backlog `docs/backlog.md` với priority + estimate]
→ [Nếu 🟠: đề xuất scope nhỏ hơn cụ thể, chờ user OK]
→ [Nếu 🔴: explain lý do + suggest alternative]

---

*Created by skill: `ba-spec` | Date: YYYY-MM-DD | Reviewer: [user name]*
