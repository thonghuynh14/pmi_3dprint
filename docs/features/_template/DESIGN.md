# Feature Design: [Feature Name]

> Output từ skill `ba-spec` PHA 2. How (technical design).

## Architecture overview

```
[Diagram or text-based architecture for this feature]
```

## Component breakdown

### Backend (Django)

**App**: `apps/[app_name]`

**New files**:
- `apps/[app]/models/[model].py` — [purpose]
- `apps/[app]/services/[service].py` — [business logic]
- `apps/[app]/selectors/[selector].py` — [read queries]
- `apps/[app]/serializers/[input/output]_serializer.py`
- `apps/[app]/views/[viewset].py`
- `apps/[app]/permissions.py` (extend)
- `apps/[app]/filters.py`
- `apps/[app]/urls.py` (extend)
- `apps/[app]/tasks.py` (if async)
- `apps/[app]/migrations/00XX_[name].py`

**Modified files**:
- [file] — [what changes]

### Frontend (Next.js)

**New files**:
- `src/app/(admin)/[route]/page.tsx` — server component
- `src/app/(admin)/[route]/_components/[name].tsx` — client component
- `src/lib/api/[resource].ts` — API client functions
- `src/lib/hooks/use-[resource].ts` — React Query hooks
- `src/lib/schemas/[resource].ts` — zod schemas
- `src/lib/types/[resource].ts` — TS types
- `src/components/[domain]/[component].tsx`

## Data Flow

```
User action
    ↓
[Frontend component / hook]
    ↓
[API call]
    ↓
[ViewSet] → [Service] → [Selector / Model]
    ↓
[Database / Cache / Storage]
    ↓
[Response] → [React Query cache] → [UI update]
```

## State Management

- **Server state**: React Query (key: `[resource]Keys.[action]`)
- **Local state**: useState (form fields, UI toggles)
- **Persisted client**: IndexedDB for POS only
- **URL state**: searchParams for filters/pagination

## API Contract

### Endpoint 1
```
POST /api/v1/[resource]/
Auth: Bearer token, role: [role]
Body:
{
  "field1": "string",
  "field2": "number"
}
Response 201:
{
  "id": "uuid",
  "field1": "string",
  ...
}
Errors:
- 400 VALIDATION_ERROR
- 403 PERMISSION_DENIED
- 409 CONFLICT_ERROR
```

### Endpoint 2
```
...
```

## Database changes

### New tables
```sql
CREATE TABLE [name] (
  id uuid PRIMARY KEY,
  ...
);
```

### New columns
```sql
ALTER TABLE [name] ADD COLUMN [col] [type];
```

### Migration plan
1. Add nullable column
2. Backfill via RunPython
3. Alter NOT NULL
4. Add index CONCURRENTLY

## Technical Decisions

### Decision 1: [Title]
- **Options considered**: A, B, C
- **Chose**: [option]
- **Because**: [reason]
- **Trade-off**: [accepted trade-off]

### Decision 2: ...

## Security considerations

- **AuthZ**: [role check at view level + permission class]
- **AuthN**: [JWT bearer required]
- **IDOR**: [query filtered by user's team/owner]
- **Input validation**: [zod (FE) + serializer (BE)]
- **Rate limit**: [if endpoint expensive]

## Performance considerations

- **Expected load**: [requests/sec, concurrent users]
- **Query optimization**: [select_related, prefetch_related, indexes]
- **Caching**: [Redis if applicable]
- **Async**: [Celery if > 500ms]

## Test strategy

- Unit: service functions, validators
- Integration: API endpoints, DB constraints
- E2E: happy path + 1-2 error paths in Playwright
- Performance: load test if expected high traffic

## Rollout plan

1. Deploy BE to staging, smoke test
2. Deploy FE to staging, manual QA
3. Internal team test 1 day
4. Deploy production
5. Monitor (Sentry, logs) 24h
6. Announce to users

## Rollback plan

If issues found:
1. Revert deploy via Vercel/Railway
2. If migration applied + irreversible: hotfix forward
3. If reversible: run reverse migration

---

*Created by skill: `ba-spec` | Date: YYYY-MM-DD*
