# 题库与 ACM 工作流 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 CodeAtlas 基础上交付系统题库、`@` 题目关联、普通/ACM 分析/ACM 解题模式、语言选择、基础代码验证和首页真实数据。

**Architecture:** 继续使用 FastAPI 服务编排和现有 SSE 流程。题库上下文由题目服务加载，私人资料由现有混合检索服务加载，ACM 提示词和输出保护放在独立模块；消息保存题目、模式和语言元数据以支持刷新恢复。

**Tech Stack:** Next.js 15、React 19、TypeScript、自定义 CSS、FastAPI、Pydantic、SQLAlchemy Async、Alembic、PostgreSQL、pgvector、pytest、Docker Compose、agent-browser。

**Spec:** `docs/superpowers/specs/2026-09-11-problem-acm-workflow-design.md`

## Global Constraints

- 不引入 LangGraph。
- 不引入 PostgreSQL checkpoint。
- 不实现 OCR、题目链接抓取、网页搜索、在线编译、OJ 提交和正式评测。
- 保持现有认证、用户隔离、知识库、普通聊天、SSE、停止、失败和重试兼容。
- 系统题目使用 `owner_user_id = NULL` 和 `source_type = system`；本阶段不开放私人题目 CRUD。
- 题库种子迁移必须幂等，不覆盖用户数据。
- ACM 分析模式不得返回完整代码；ACM 解题模式不得声称通过在线评测。
- 生产代码前先写一个会失败的测试，并确认失败原因是缺少目标行为。

---

### Task 1: 校正文档基线并建立题库契约

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model.md`
- Modify: `docs/development-baseline.md`
- Modify: `docs/frontend-screen-map.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/technical-stack.md`
- Test: none; this task updates approved written contracts only.

**Interfaces:**
- Produces the canonical mode values `normal`, `acm_analysis`, `acm_solution` and language values `cpp`, `java`, `python`.
- Produces the canonical problem fields and API paths used by later tasks.

- [ ] **Step 1: Update the written contract**

Document the paths, fields, error behavior, and no-LangGraph constraint. Do not implement database or route behavior in this task.

- [ ] **Step 2: Review compatibility points**

Confirm that the existing router registration, `ChatRequest`, `MessageResponse`, and migration head are the only compatibility points later tasks extend. No source files are changed in this task.

---

### Task 2: Add problem and message-context data model

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/migrations/versions/0007_problem_acm_workflow.py`
- Test: `backend/tests/test_problem_models.py`
- Test: `backend/tests/test_problem_contract.py`

**Interfaces:**
- Produces `Problem`, `ProblemSummary`, `ProblemResponse`, and `ProblemPage`.
- Produces `Message.problem_id`, `Message.mode`, and `Message.solution_language`.

- [ ] **Step 1: Write failing model and schema tests**

```python
def test_problem_model_exposes_search_and_ownership_fields():
    from app.models import Problem

    problem = Problem(title="A+B", source_type="system", difficulty="入门", tags=["基础输入输出"])
    assert problem.owner_user_id is None
    assert problem.tags == ["基础输入输出"]
    assert "ix_problems_search_vector" in {index.name for index in Problem.__table__.indexes}


def test_chat_request_accepts_acm_modes_and_rejects_unknown_mode():
    import pytest
    from pydantic import ValidationError
    from app.schemas import ChatRequest

    assert ChatRequest(content="分析", mode="acm_analysis").mode == "acm_analysis"
    assert ChatRequest(content="解题", mode="acm_solution", solution_language="python").solution_language == "python"
    with pytest.raises(ValidationError):
        ChatRequest(content="x", mode="other")
```

- [ ] **Step 2: Run tests and verify expected failure**

Run: `cd backend; pytest tests/test_problem_models.py tests/test_problem_contract.py -q`

Expected: FAIL because `Problem` does not exist and `mode` rejects ACM values.

- [ ] **Step 3: Implement the model, schema, and migration**

Create `problems` with nullable owner, source type, slug, searchable text, JSON examples/constraints/languages, and ownership/search indexes. Add nullable message context columns and foreign key `messages.problem_id -> problems.id`. Use `0006_job_reliability` as `down_revision`. Do not insert seed rows in this migration.

- [ ] **Step 4: Run focused tests and inspect migration metadata**

Run: `cd backend; pytest tests/test_problem_models.py tests/test_problem_contract.py -q`

Expected: PASS. Also run `python -m compileall app migrations` and confirm the migration revision is `0007_problem_acm_workflow` with down revision `0006_job_reliability`.

---

### Task 3: Add idempotent system problem seed data

**Files:**
- Modify: `backend/migrations/versions/0007_problem_acm_workflow.py`
- Test: `backend/tests/test_problem_seed.py`

**Interfaces:**
- Produces five system problems with stable slugs and complete required fields.

- [ ] **Step 1: Write the failing seed test**

```python
def test_problem_migration_contains_idempotent_seed_rows():
    from pathlib import Path

    source = Path(__file__).parents[1].joinpath("migrations/versions/0007_problem_acm_workflow.py").read_text(encoding="utf-8")
    for slug in ("hello-world", "a-plus-b", "basic-io", "branch-judgment", "simple-loop"):
        assert slug in source
    assert "ON CONFLICT" in source
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `cd backend; pytest tests/test_problem_seed.py -q`

Expected: FAIL because the migration has no seed statements.

- [ ] **Step 3: Add idempotent inserts**

Insert Hello World, A+B, basic input/output, branch judgment, and simple loop with Chinese descriptions, examples, constraints, tags, and `supported_languages = ["cpp", "java", "python"]`. Use stable UUIDs or stable slugs and `ON CONFLICT (slug) DO NOTHING`.

- [ ] **Step 4: Run focused tests**

Run: `cd backend; pytest tests/test_problem_seed.py -q`

Expected: PASS. In integration verification, run Alembic upgrade twice and verify the row count remains five for a clean database.

---

### Task 4: Implement problem service and API

**Files:**
- Create: `backend/app/services/problems.py`
- Create: `backend/app/routers/problems.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_problems_api.py`

**Interfaces:**
- Produces `search_problems(session, user_id, query, difficulty, tag, page, page_size) -> ProblemPage`.
- Produces `get_owned_problem(session, problem_id, user_id) -> Problem`.
- Registers `GET /api/v1/problems` and `GET /api/v1/problems/{problem_id}`.

- [ ] **Step 1: Write failing API tests**

```python
@pytest.mark.asyncio
async def test_problem_list_filters_system_rows_and_returns_page(monkeypatch):
    response = await api_client.get("/api/v1/problems?query=A%2BB&difficulty=入门&page=1&page_size=10")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["slug"] == "a-plus-b"
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_problem_detail_hides_other_users_private_problem():
    response = await api_client.get(f"/api/v1/problems/{other_user_problem_id}")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend; pytest tests/test_problems_api.py -q`

Expected: FAIL with 404 because the router is not registered.

- [ ] **Step 3: Implement query and detail behavior**

Use parameterized SQLAlchemy filters. Search title, slug, statement and tags with PostgreSQL full-text search; use exact difficulty and tag filters. Clamp page size to 1..100. Apply `owner_user_id IS NULL OR owner_user_id == user_id` to every query.

- [ ] **Step 4: Register the router and run tests**

Run: `cd backend; pytest tests/test_problems_api.py -q`

Expected: PASS, including unauthenticated rejection and cross-user 404.

---

### Task 5: Connect problem context to chat and persist metadata

**Files:**
- Create: `backend/app/services/problem_context.py`
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_chat_problem_context.py`
- Test: `backend/tests/test_conversations_runtime.py`

**Interfaces:**
- Produces `resolve_problem_context(session, problem_id, user_id) -> Problem | None`.
- Produces `build_problem_prompt(problem, user_content, mode, language) -> str`.
- Extends persisted user and assistant messages with the same problem/mode/language metadata.

- [ ] **Step 1: Write failing context and validation tests**

```python
def test_analysis_requires_a_problem_id():
    from app.services.problem_context import validate_chat_context

    with pytest.raises(ValueError, match="problem"):
        validate_chat_context("acm_analysis", None, None)


def test_solution_requires_supported_language():
    from app.services.problem_context import validate_chat_context

    with pytest.raises(ValueError, match="language"):
        validate_chat_context("acm_solution", uuid.uuid4(), None)
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `cd backend; pytest tests/test_chat_problem_context.py -q`

Expected: FAIL because the context service does not exist.

- [ ] **Step 3: Implement validation and ownership loading**

Require a problem for both ACM modes, require one of `cpp`, `java`, `python` for solution mode, clear language for analysis mode, and raise an HTTP 404 when the loaded problem is not visible to the user.

- [ ] **Step 4: Integrate metadata into the stream endpoint**

Load the problem before model generation, include its content in the prompt, set `problem_id`, `mode`, and `solution_language` on both persisted messages, and keep ordinary mode behavior unchanged when no problem is selected.

- [ ] **Step 5: Run focused and regression tests**

Run: `cd backend; pytest tests/test_chat_problem_context.py tests/test_conversations_runtime.py -q`

Expected: PASS, including existing retrieval failure and model failure behavior.

---

### Task 6: Implement ACM prompts, output guard, and code checks

**Files:**
- Create: `backend/app/acm_workflow.py`
- Create: `backend/app/code_validation.py`
- Modify: `backend/app/routers/conversations.py`
- Test: `backend/tests/test_acm_workflow.py`
- Test: `backend/tests/test_code_validation.py`

**Interfaces:**
- Produces `build_acm_prompt(problem, user_content, mode, language, knowledge_context) -> str`.
- Produces `sanitize_analysis_output(text) -> str`.
- Produces `validate_solution_code(language, code) -> dict`.

- [ ] **Step 1: Write failing prompt and guard tests**

```python
def test_analysis_prompt_requires_explanation_without_complete_code():
    prompt = build_acm_prompt(problem, "怎么做", "acm_analysis", None, "")
    assert "不得输出完整代码" in prompt
    assert "时间复杂度" in prompt


def test_analysis_output_removes_fenced_complete_code():
    result = sanitize_analysis_output("思路如下。\n```cpp\nint main() {}\n```")
    assert "int main" not in result
    assert "分析模式不输出完整代码" in result
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `cd backend; pytest tests/test_acm_workflow.py tests/test_code_validation.py -q`

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement minimal prompts and guard**

Use explicit headings for problem goal, input/output, constraints, examples, algorithm, correctness, complexity, boundaries and hints. Treat retrieved documents as untrusted. Analysis mode must not ask for hidden reasoning or a full program. Remove fenced code blocks from analysis output.

- [ ] **Step 4: Implement basic language checks**

For Python, parse the extracted code with `ast.parse`. For C++ and Java, check a non-empty code block, balanced delimiters and a main entry point. Return `{status, language, message}` and never claim online evaluation.

- [ ] **Step 5: Run focused tests**

Run: `cd backend; pytest tests/test_acm_workflow.py tests/test_code_validation.py -q`

Expected: PASS.

---

### Task 7: Extend SSE contracts and retrieval integration

**Files:**
- Modify: `backend/app/routers/conversations.py`
- Modify: `backend/app/services/retrieval_service.py`
- Modify: `backend/app/retrieval.py`
- Test: `backend/tests/test_acm_stream.py`

**Interfaces:**
- Produces `context.resolved` with problem and retrieval metadata.
- Keeps existing retrieval event names and citation validation behavior.

- [ ] **Step 1: Write failing stream tests**

```python
@pytest.mark.asyncio
async def test_acm_analysis_stream_emits_context_and_never_persists_complete_code(monkeypatch):
    monkeypatch.setattr(conversations_module, "model_stream", fake_analysis_stream)
    response = await client.post(stream_url, json={"content": "分析", "mode": "acm_analysis", "problem_id": str(problem_id)})
    assert "event: context.resolved" in response.text
    assert "分析模式不输出完整代码" in response.text
```

- [ ] **Step 2: Run test and verify failure**

Run: `cd backend; pytest tests/test_acm_stream.py -q`

Expected: FAIL because the current stream has no problem context event and always builds the ordinary prompt.

- [ ] **Step 3: Integrate selected knowledge retrieval**

When groups or attachments are supplied, use the existing retriever with a query composed from the problem title, tags and user content. Keep ordinary retrieval failure semantics unchanged.

- [ ] **Step 4: Emit compatible events and persist final metadata**

Emit `run.started`, `context.resolved`, existing retrieval events, deltas, validated citations, and a final event containing message ID, mode, problem ID and language. Sanitize analysis output before persistence and before `message.final`.

- [ ] **Step 5: Run stream and full backend tests**

Run: `cd backend; pytest tests/test_acm_stream.py tests/test_conversations_runtime.py -q` and then `pytest -q`.

Expected: all existing tests and new tests pass.

---

### Task 8: Build题库列表、详情和首页 dashboard

**Files:**
- Modify: `frontend/src/app/problems/page.tsx`
- Create: `frontend/src/app/problems/[id]/page.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/ProblemCard.tsx`
- Create: `frontend/src/components/ProblemFilters.tsx`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Consumes the problem list/detail and dashboard APIs.
- Produces responsive pages with loading, empty, error and authenticated states.

- [ ] **Step 1: Add browser-level failing checks**

Run the existing app with a clean test account and record the current `/problems` placeholder as the failing baseline. The acceptance assertions are: a problem title is visible, changing the search field changes the request, and clicking a card opens `/problems/<id>`.

- [ ] **Step 2: Implement the list and detail pages**

Use `apiFetch`, debounce only the search request, keep independent filters in URL search parameters, show stable row dimensions, and render a clear empty result state. Detail page displays all problem fields and links to chat with `problem_id` and selected mode.

- [ ] **Step 3: Implement dashboard data loading**

Load `/api/v1/dashboard` only for authenticated users. Use actual counts and conversation IDs. Render a first-session empty state instead of static numbers.

- [ ] **Step 4: Build and run browser checks**

Run: `cd frontend; npm run build`; then use agent-browser at desktop and mobile widths to verify the list, detail, navigation, no horizontal overflow, and dashboard empty/non-empty states.

Expected: production build passes and the placeholder is gone.

---

### Task 9: Add `@` selector, mode menu, and language gate

**Files:**
- Modify: `frontend/src/app/chat/page.tsx`
- Create: `frontend/src/components/ProblemMentionPicker.tsx`
- Create: `frontend/src/components/ModeSelector.tsx`
- Create: `frontend/src/components/LanguageDialog.tsx`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- `ProblemMentionPicker` emits `onSelect(problem: ProblemSummary)` and `onClear()`.
- `ModeSelector` emits `onChange(mode: ChatMode)`.
- `LanguageDialog` resolves `cpp`, `java`, or `python`.

- [ ] **Step 1: Add browser-level failing checks**

Verify the current chat cannot select a problem, cannot open ACM modes, and sends `mode: normal`; keep these as the failing interaction baseline.

- [ ] **Step 2: Implement `@` picker**

Track the token after the latest `@`, call the problem list endpoint, support ArrowUp/ArrowDown/Enter/Escape, and show the selected problem as removable context. Do not place complete problem text into the editable message body.

- [ ] **Step 3: Implement mode selection and language dialog**

Show all three modes. Opening ACM solution mode requires a language selection before sending. Keep controls disabled during generation with stable dimensions.

- [ ] **Step 4: Send problem and mode fields**

Replace the hardcoded `mode: "normal"` body with current mode, `problem_id`, and `solution_language`. Handle `context.resolved`, final metadata, retrieval errors and analysis guard messages.

- [ ] **Step 5: Run build and browser checks**

Run: `cd frontend; npm run build`; then use agent-browser to test `@` selection, mode switching, language selection, disabled states and mobile layout.

Expected: the browser request contains the selected problem ID and correct mode/language.

---

### Task 10: Add cross-layer regression and deployment verification

**Files:**
- Modify: `docs/browser-test-plan.md`
- Modify: `docs/browser-test-results.md`
- Modify: `docs/roadmap.md`
- Test: `backend/tests/test_cross_user_problem_access.py`

**Interfaces:**
- Produces the final documented acceptance record for题库 and ACM flows.

- [ ] **Step 1: Write failing isolation regression test**

```python
@pytest.mark.asyncio
async def test_user_cannot_attach_or_chat_with_another_users_private_problem():
    response = await client.get(f"/api/v1/problems/{private_problem_id}", headers=other_user_headers)
    assert response.status_code == 404

    response = await client.post(stream_url, headers=other_user_headers, json={"content": "x", "mode": "acm_analysis", "problem_id": str(private_problem_id)})
    assert response.status_code in (400, 404, 422)
```

- [ ] **Step 2: Run the regression test and verify failure**

Run: `cd backend; pytest tests/test_cross_user_problem_access.py -q`

Expected: FAIL until the problem ownership filter is exercised through both detail and chat paths.

- [ ] **Step 3: Run complete verification**

Run: `cd backend; pytest -q`; `cd frontend; npm run build`; `docker compose config`; then run the documented browser matrix against the Compose services.

- [ ] **Step 4: Record results and update roadmap**

Document passing and limited cases, state that no OJ evaluation exists, and record that LangGraph/checkpoint remains future work. Do not claim tests that were not run.

## Plan Self-Review

- Spec coverage: tasks 2-3 cover model and seed data; Task 4 covers API; Tasks 5-7 cover association, modes, prompts, RAG and SSE; Tasks 8-9 cover UI and homepage; Task 10 covers isolation and regression.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation step is required.
- Type consistency: mode names, language names, API paths, and service signatures are consistent across tasks.
- Migration chain: `0007_problem_acm_workflow` follows `0006_job_reliability`.
- Explicit gap: no formal online compilation is included by design.
