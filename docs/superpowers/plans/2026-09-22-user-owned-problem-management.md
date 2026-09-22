# 用户题库管理 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with tests before implementation changes.

**Goal:** 为每个账号建立独立可管理的题库，并将题库页面改为带唯一 ID 的索引列表与参考图风格的题目详情。

**Architecture:** 系统题目保留为 `owner_user_id = NULL` 的注册模板；注册事务复制模板到当前用户，历史用户由迁移补齐。题库 API 只允许当前用户访问和修改自己的题目，前端通过列表、右侧抽屉表单和详情页操作 CRUD。

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, Next.js 15, React 19, TypeScript, existing `react-markdown` dependency for a later phase.

**Spec:** `docs/superpowers/specs/2026-09-22-user-owned-problem-management-design.md`

## Global Constraints

- System problem rows remain templates and use `owner_user_id = NULL` and `source_type = system`.
- Every registered user receives copied default rows with `owner_user_id = user.id` and `source_type = default`.
- Every problem write checks ownership on the server; UUID IDs are immutable.
- Do not add the Markdown source/preview editor in this implementation.
- Existing ACM chat links and problem context behavior must continue to work.

---

### Task 1: Lock down problem ownership and CRUD contracts

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/problems.py`
- Test: `backend/tests/test_problems_api.py`

**Interfaces:**
- `ProblemSummary` exposes `owner_user_id` and `source_type`.
- Add `ProblemCreate`, `ProblemUpdate`, and `ProblemResponse` validation for shared problem fields.
- Add service functions `create_problem`, `update_problem`, `delete_problem`, and `clone_system_problems`.

- [ ] Write tests for blank field rejection, ownership filtering, and system/template rows not being writable.
- [ ] Run `cd backend; pytest tests/test_problems_api.py -q` and confirm the new tests fail because the schemas and service methods are absent.
- [ ] Implement normalized schemas and service methods. Generate UUIDs in the service, create a unique `custom-<uuid hex>` slug, filter search to `Problem.owner_user_id == user_id`, and raise 404 for non-owned resources.
- [ ] Re-run the focused test file and confirm it passes.

### Task 2: Add registration cloning and historical-account migration

**Files:**
- Modify: `backend/app/routers/auth.py`
- Create: `backend/migrations/versions/0011_user_owned_problem_copies.py`
- Modify: `backend/tests/test_problem_seed.py`
- Create: `backend/tests/test_problem_ownership.py`

**Interfaces:**
- `clone_system_problems(session, user_id)` copies all `source_type = system` rows and returns the new `Problem` instances.
- Registration calls cloning after flushing the new user and before committing the refresh token transaction.

- [ ] Write a test that a new user receives a copied row with a new UUID, the user owner ID, and `source_type = default`.
- [ ] Run the focused tests and confirm failure before implementation.
- [ ] Call `clone_system_problems` from registration and add migration `0011` that inserts one owned copy of every system template for every existing user, skipping an already-present `(owner_user_id, source template slug)` copy by matching the generated `default-<template-slug>` slug.
- [ ] Run `cd backend; pytest tests/test_problem_seed.py tests/test_problem_ownership.py -q` and verify migration source and cloning behavior.

### Task 3: Expose authenticated problem CRUD routes

**Files:**
- Modify: `backend/app/routers/problems.py`
- Modify: `backend/app/main.py` only if route registration requires it
- Modify: `backend/tests/test_problems_api.py`

**Interfaces:**
- `POST /api/v1/problems` accepts `ProblemCreate` and returns `ProblemResponse` with status 201.
- `PATCH /api/v1/problems/{problem_id}` accepts `ProblemUpdate` and returns `ProblemResponse`.
- `DELETE /api/v1/problems/{problem_id}` returns 204.

- [ ] Write route contract tests for create, update, delete, and foreign-user 404 behavior using the existing router dependency patterns.
- [ ] Run the focused API tests and observe expected failures for missing routes.
- [ ] Register the three routes, pass the authenticated user ID and async session to the service, commit through the route workflow, and return the response models.
- [ ] Run the complete backend problem/auth test subset and confirm all pass.

### Task 4: Build the indexed problem list and CRUD drawer

**Files:**
- Modify: `frontend/src/components/ProblemCard.tsx` or replace its export with an indexed row component
- Modify: `frontend/src/components/ProblemFilters.tsx`
- Modify: `frontend/src/app/problems/page.tsx`
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/components/ProblemEditor.tsx`

**Interfaces:**
- The list consumes `ProblemSummary` with `owner_user_id` and `source_type`.
- `ProblemEditor` accepts `problem: ProblemResponse | null`, `onSaved`, and `onClose`; it posts or patches `/problems` using the existing `apiFetch` helper.

- [ ] Add a focused frontend test or compile-level contract for the editor payload normalization before adding the implementation.
- [ ] Run the available frontend test command and confirm the new contract is red.
- [ ] Implement the table-like list: full UUID in the first column, title and metadata columns, filters, pagination, create button, edit/delete actions, drawer form, loading/empty/error states, and confirm dialog.
- [ ] Replace card-grid CSS with dense index rows while preserving the current project palette, typography, focus styles, and mobile wrapping behavior.
- [ ] Run `cd frontend; npm run build` and the focused frontend tests.

### Task 5: Reshape the problem detail page and verify the workflow

**Files:**
- Modify: `frontend/src/app/problems/[id]/page.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`

**Interfaces:**
- Detail page renders full UUID, title, difficulty, tags, source, timestamps, statement sections, and a right-side action rail.
- Edit and delete actions call the same CRUD endpoints and return to `/problems` after successful deletion.

- [ ] Add a build-level check for detail-page fields and action links before changing markup.
- [ ] Implement the header metadata strip, two-column desktop layout, compact action rail, responsive single-column fallback, and current ACM analysis/solution links.
- [ ] Document the new endpoints and user-owned model semantics.
- [ ] Run backend tests, frontend build, start the dev server, and use browser QA at desktop and mobile widths for list, create, edit, delete, detail, and empty states.
