# Feature Spec: [Feature Name]

> Output từ skill `ba-spec` PHA 2. What & Why của feature.

## Overview
[1-liner]

## Stakeholders

- **Primary user**: [role]
- **Secondary**: [role]
- **PM/Owner**: [name]

## User Flow

```
1. [Step 1 — user action]
2. [Step 2 — system response]
3. [Step 3 — ...]
4. [Step 4 — outcome]
```

## Acceptance Criteria (Given-When-Then)

### AC-1: [Tên ngắn]
```
Given [precondition]
And [precondition 2]
When [user action]
Then [expected result]
And [side effect]
```

### AC-2: [Tên ngắn]
```
Given ...
When ...
Then ...
```

### AC-3: [Error case]
```
Given ...
When [invalid action]
Then [system rejects]
And [user sees error message Y]
```

## Edge Cases

- [ ] Edge case 1: [behavior expected]
- [ ] Edge case 2: ...
- [ ] Concurrent edit by 2 users
- [ ] Permission denied (role insufficient)
- [ ] Network failure mid-action
- [ ] Empty state (0 records)
- [ ] Large data (1000+ records)

## Business Rules Applied

- BR-XXX: [reference business-rules.md]
- BR-YYY: ...

## Permissions

| Role | Can do |
|---|---|
| Super Admin | All |
| Catalog Manager | ... |
| Production Manager | ... |
| Channel Operator | ... |
| Designer | ... |
| Cashier | ... |

## Out of Scope

Explicitly NOT in this feature:
- [Item X] — will be in feature `NN-other-feature`
- [Item Y] — Phase 2

## Dependencies

**Depends on**:
- Feature `NN-...` must be done first
- External: Shopee sandbox access, ...

**Blocks**:
- Feature `NN-...` waits for this

## Success Criteria

- All AC pass
- Test coverage > target (xem conventions.md)
- Code review approved
- E2E test green
- Manual QA bằng checklist

---

*Created by skill: `ba-spec` | Date: YYYY-MM-DD*
