# Code Review: Phase 5 — Project Entity + DB Models

**Reviewer:** code-reviewer | **Date:** 2026-03-22
**Scope:** 11 files | ~1,150 LOC | Backend models, parser, schemas, routes + Frontend pages

---

## Overall Assessment

Solid implementation. Models are well-structured with proper FK cascades and `delete-orphan` relationships. Credential encryption reuses the proven AES-256-GCM pipeline. Frontend pages are clean and consistent with the existing UI. However, several security and data-integrity issues need attention before merging.

---

## Critical Issues

### C1. No Authorization/RBAC on Project Endpoints (Security)
**File:** `backend/api/routes/project-routes.py`
**Impact:** Any authenticated user can update/delete/add credentials to ANY project they can see. The `_require_auth()` helper only checks "is logged in" — never checks project membership or role.

Compare: the existing permission middleware (`require_permission()`) enforces workspace-level RBAC. Projects lack equivalent guards.

**Affected endpoints:**
- `PATCH /api/projects/{id}` — any user can rename/archive any project
- `DELETE /api/projects/{id}` — any user can archive any project
- `POST /api/projects/{id}/credentials` — any user can store credentials on any project
- `POST /api/projects/{id}/members` — any user can add members
- `DELETE /api/projects/{id}/members/{uid}` — any user can remove members

**Fix:** Add role checks using the `ProjectMember.role_name` field. At minimum:
```python
async def _require_project_role(session, project_id: str, user_id: str, min_role: str) -> ProjectMember:
    member = (await session.execute(
        sa_select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="Not a project member")
    # Check role hierarchy: workspace-admin > user > viewer
    if ROLE_RANK.get(member.role_name, 0) < ROLE_RANK.get(min_role, 0):
        raise HTTPException(status_code=403, detail="Insufficient role")
    return member
```

### C2. Credential Data Logged in Request Body (Security)
**File:** `backend/api/routes/project-routes.py:298-329`
**Impact:** `AddCredentialRequest.credential_json` is a plain string in the POST body. If audit middleware logs request bodies (which it does via `AuditMiddleware`), raw credentials flow into `audit_logs` table in plaintext.

**Fix:** Either:
- Exclude `/api/projects/*/credentials` from audit body logging, OR
- Accept credentials as `SecretStr` in Pydantic and ensure serialization masks the value, OR
- Encrypt client-side before transmission (more complex)

### C3. `_sync_modules` Deletes Modules With Associated Runs (Data Loss)
**File:** `backend/api/routes/project-routes.py:412-435`
**Impact:** When YAML config is updated and a module is removed from config, `_sync_modules` deletes the `ProjectModule` row. Due to `ondelete="CASCADE"` on `ProjectRun.module_id`, all historical run records for that module are permanently deleted.

**Fix:** Soft-delete modules (set status="removed") instead of hard-deleting, or check for associated runs before deletion:
```python
for name, mod in existing.items():
    if name not in new_names:
        run_count = (await session.execute(
            sa_select(func.count()).where(ProjectRun.module_id == mod.id)
        )).scalar()
        if run_count > 0:
            mod.status = "removed"
            session.add(mod)
        else:
            await session.delete(mod)
```

---

## High Priority

### H1. JSONB Column Type Annotation Mismatch
**File:** `backend/db/models.py:578, 604`
**Impact:** `depends_on` and `assigned_modules` are typed `Mapped[dict]` but store JSON arrays (lists), and `default=list` produces `[]`. SQLAlchemy may not complain at runtime, but the type hint is wrong and will confuse type checkers and future developers.

**Fix:**
```python
depends_on: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
assigned_modules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
```

### H2. `list_projects` Lacks Org Scoping for Null org_id
**File:** `backend/api/routes/project-routes.py:146-156`
**Impact:** When `user.org_id` is `None` (user not in any org), the query returns ALL non-archived projects across all orgs because the `org_id` filter is skipped. This leaks data across organizational boundaries.

**Fix:**
```python
if org_id:
    q = q.where(Project.org_id == org_id)
else:
    q = q.where(Project.org_id.is_(None))
```

### H3. No `name` Length Validation in Schema
**File:** `backend/api/schemas/project-schemas.py:14-25`
**Impact:** `CreateProjectRequest.name` only validates non-empty after strip. A user could submit a 10,000-char name, which exceeds the `String(128)` DB column and causes an unhandled 500 error.

**Fix:** Add length constraint:
```python
@field_validator("name")
@classmethod
def name_not_empty(cls, v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Project name is required")
    if len(v) > 128:
        raise ValueError("Project name must be 128 characters or less")
    return v
```

### H4. `AddMemberRequest.role_name` Not Validated
**File:** `backend/api/schemas/project-schemas.py:42-45`
**Impact:** Any arbitrary string accepted as `role_name`. There's no enum or validation, so a user could set `role_name="superadmin"` or any garbage value, defeating future RBAC logic.

**Fix:**
```python
VALID_ROLES = {"viewer", "user", "workspace-admin"}

@field_validator("role_name")
@classmethod
def valid_role(cls, v: str) -> str:
    if v not in VALID_ROLES:
        raise ValueError(f"role_name must be one of: {', '.join(sorted(VALID_ROLES))}")
    return v
```

### H5. Self-Dependency Not Detected in DAG Validation
**File:** `backend/core/project-config-parser.py:133-162`
**Impact:** A module with `depends_on: [itself]` passes the "unknown module" check (line 140) because the module name IS in `module_names`. It also passes the cycle detection because `_visit` checks `in_stack` after the "already visited" early return — but on first visit for a self-referencing module, `in_stack.add(name)` fires, then `dep_map[name]` contains `name` again, and `_visit(name)` is called recursively, hitting `in_stack` check correctly.

Actually, after tracing through: `_visit("A")` -> `in_stack = {"A"}` -> iterates deps -> `_visit("A")` -> `"A" in in_stack` = True -> raises. **This IS correctly detected.** Disregard.

---

## Medium Priority

### M1. `create_project` Duplicate Check Excludes Archived Projects
**File:** `backend/api/routes/project-routes.py:104-112`
**Impact:** A user can create a new project with the same name as an archived one. The DB has `UniqueConstraint("org_id", "name")` which will cause a 500 IntegrityError because the constraint doesn't exclude archived rows.

**Fix:** Either:
- Remove `Project.status != "archived"` from the duplicate check (match DB constraint), OR
- Add a partial unique index in DB: `CREATE UNIQUE INDEX ... WHERE status != 'archived'` and drop the table-level constraint

### M2. `_project_detail_response` Hardcodes Empty Runs List
**File:** `backend/api/routes/project-routes.py:382`
**Impact:** `runs=[]` is always returned in the detail response, even though the schema has `runs: list[ProjectRunResponse]`. The `_get_project_or_404` doesn't eagerly load runs, and the detail response helper ignores them. Users see "Runs" tab always empty on the detail page.

**Fix:** Either eagerly load runs in `_get_project_or_404`:
```python
selectinload(Project.runs).selectinload(ProjectRun.module),
```
Or query runs separately in `get_project` and pass them to the response builder.

### M3. `archive_project` DELETE Returns 204 But Doesn't Actually Delete
**File:** `backend/api/routes/project-routes.py:199-206`
**Impact:** The endpoint is `DELETE` with `status_code=204` but performs a soft-delete (status="archived"). This is semantically fine, but the `list_projects` still shows archived projects to users without org_id (see H2). Also, there's no way to un-archive a project through the API (the `update_project` PATCH does allow setting status back to "active", so this is OK).

Minor: no audit log entry for archival.

### M4. `UpdateProjectRequest` Allows Setting `name` to Empty String
**File:** `backend/api/schemas/project-schemas.py:28-39`
**Impact:** `name: Optional[str] = None` — when provided, no strip/empty check runs. A PATCH with `{"name": ""}` sets the project name to empty string. The `CreateProjectRequest` validates this, but `UpdateProjectRequest` does not.

**Fix:** Add same validator:
```python
@field_validator("name")
@classmethod
def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
    if v is not None:
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        if len(v) > 128:
            raise ValueError("Project name must be 128 characters or less")
    return v
```

### M5. Frontend Error State Not Shown on Detail Page
**File:** `frontend/src/components/projects/project-detail-page.tsx:33-36`
**Impact:** On fetch error, silently navigates to `/projects` with no toast/error message. User has no idea why they were redirected.

**Fix:** Show error state or display a toast notification before navigating.

### M6. `list_projects` Has No Pagination
**File:** `backend/api/routes/project-routes.py:146-156`
**Impact:** Returns all non-archived projects in one query. For orgs with hundreds of projects, this will be slow and send large payloads.

**Fix:** Add `skip`/`limit` query parameters (consistent with `list_runs` which already uses `.limit(50)`).

---

## Low Priority

### L1. `_require_auth` Duplicated Across Route Files
Multiple route files define their own `_require_auth`. Consider extracting to a shared `backend/api/deps.py` module.

### L2. Frontend `ProjectListPage` Filters Client-Side
**File:** `frontend/src/components/projects/project-list-page.tsx:35-38`
Filtering all projects in-browser is fine for now but won't scale. Consider server-side search query param in future.

### L3. `STATUS_COLORS` Duplicated Between List and Detail Pages
Both `project-list-page.tsx` and `project-detail-page.tsx` define their own `STATUS_COLORS`. Extract to a shared constant.

### L4. Missing `key` Prop Warning Risk
**File:** `frontend/src/components/projects/project-detail-page.tsx:71`
The tabs array uses `.map()` with `key={key}` which is correct. No issue.

---

## Positive Observations

1. **Credential security done right** — `ProjectCredentialResponse` never exposes raw `credential_data`; encryption reuses battle-tested `state-encryption.py`; `LargeBinary` column stores encrypted bytes directly.
2. **DAG validation is correct** — Topological sort properly detects cycles and unknown dependency references.
3. **`cascade="all, delete-orphan"`** on Project relationships ensures clean removal of related records.
4. **YAML config parsing is defensive** — Type checks on each section, graceful error messages with context.
5. **Frontend UX is polished** — Empty states, loading indicators, search, status badges, mode toggle on create dialog.
6. **`_sync_modules`** correctly handles add/update/remove — just needs the soft-delete fix for modules with runs.
7. **Router registration** in `main.py` follows established pattern cleanly.
8. **TypeScript types** accurately mirror backend Pydantic schemas with proper optional/null handling.

---

## Recommended Actions (Priority Order)

1. **[CRITICAL]** Add project-level RBAC checks to mutation endpoints (C1)
2. **[CRITICAL]** Prevent credential plaintext from being audit-logged (C2)
3. **[CRITICAL]** Soft-delete modules with existing runs instead of hard-delete (C3)
4. **[HIGH]** Fix `Mapped[dict]` -> `Mapped[list]` for JSONB array columns (H1)
5. **[HIGH]** Fix org scoping for null org_id in list_projects (H2)
6. **[HIGH]** Add name length validation to create/update schemas (H3, M4)
7. **[HIGH]** Validate role_name against allowed values (H4)
8. **[MEDIUM]** Fix unique constraint vs soft-delete conflict (M1)
9. **[MEDIUM]** Load runs in project detail response (M2)
10. **[MEDIUM]** Add pagination to list_projects (M6)

---

## Metrics

| Metric | Value |
|--------|-------|
| Type Coverage (Backend) | ~90% (JSONB columns under-typed) |
| Type Coverage (Frontend) | ~95% (proper interfaces for all API types) |
| Test Coverage | Not evaluated (no test files in scope) |
| Linting Issues | Not run (no build commands executed) |
| Security Issues | 3 critical |
| Data Integrity Issues | 2 (cascade delete + unique constraint conflict) |

---

## Unresolved Questions

1. Should `ProjectMember` track `updated_at` for role changes, or is `joined_at` sufficient?
2. Is there a planned endpoint for decrypting credentials at runtime for Terraform execution? The current write-only pattern needs a read path for the runner.
3. Should the `Project.status` enum be enforced at the DB level (CHECK constraint) in addition to the Pydantic validator?
4. Will `_sync_modules` need to handle module renames (same path, different name) as updates rather than delete+create?
