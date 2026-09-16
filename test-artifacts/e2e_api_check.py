"""End-to-end API smoke test for the running CodeAtlas stack.

Exercises auth, profile, conversation management, streaming chat, citations
and the knowledge base against http://backend:8000 (compose network).
"""
import json
import sys
import time
import traceback
import uuid

import httpx

BASE = "http://backend:8000/api/v1"
TIMEOUT = httpx.Timeout(timeout=180.0, connect=10.0)
STAMP = uuid.uuid4().hex[:10]

failures = []
checks = []


def record(name, ok, detail=""):
    checks.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}"[:400], flush=True)
    if not ok:
        failures.append((name, detail))


def call(client, method, path, **kwargs):
    response = client.request(method, f"{BASE}{path}", **kwargs)
    return response


def expect(name, response, statuses, allow_body_error=False):
    ok = response.status_code in statuses
    body = response.text[:300].replace("\n", " ")
    if ok and allow_body_error:
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if isinstance(payload, dict) and payload.get("code"):
            ok = False
    record(name, ok, f"status={response.status_code} body={body}")
    return response


def read_sse(client, path, payload, headers=None):
    events = []
    with client.stream("POST", f"{BASE}{path}", json=payload, headers=headers or {}) as response:
        if response.status_code != 200:
            response.read()
            return response.status_code, events
        current = None
        for line in response.iter_lines():
            if not line:
                if current is not None:
                    events.append(current)
                    current = None
                continue
            if line.startswith("event:"):
                current = {"event": line.split(":", 1)[1].strip(), "data": ""}
            elif line.startswith("data:") and current is not None:
                current["data"] += line.split(":", 1)[1].strip()
        if current is not None:
            events.append(current)
    return 200, events


def event_names(events):
    return [event["event"] for event in events]


def main():
    client = httpx.Client(timeout=TIMEOUT, follow_redirects=True)
    email = f"codex-e2e-{STAMP}@example.com"
    password = "CodexPass123!"

    # --- auth -------------------------------------------------------------
    response = call(client, "POST", "/auth/register", json={"email": email, "password": password, "nickname": "Codex E2E"})
    expect("POST /auth/register", response, {201})
    token = response.json().get("access_token", "") if response.status_code == 201 else ""
    refresh = response.json().get("refresh_token", "") if response.status_code == 201 else ""

    response = call(client, "POST", "/auth/register", json={"email": email, "password": password, "nickname": "Dup"})
    expect("POST /auth/register duplicate rejected", response, {400, 409})

    response = call(client, "POST", "/auth/login", json={"email": email, "password": password})
    expect("POST /auth/login", response, {200})
    if response.status_code == 200:
        token = response.json().get("access_token", token)
        refresh = response.json().get("refresh_token", refresh)

    response = call(client, "POST", "/auth/login", json={"email": email, "password": "wrong-password"})
    expect("POST /auth/login wrong password rejected", response, {401})

    response = call(client, "POST", "/auth/refresh", json={"refresh_token": refresh})
    expect("POST /auth/refresh", response, {200})

    auth = {"Authorization": f"Bearer {token}"}

    response = call(client, "GET", "/users/me", headers=auth)
    expect("GET /users/me", response, {200})

    response = call(client, "GET", "/users/me")
    expect("GET /users/me without token rejected", response, {401, 403})

    response = call(client, "PATCH", "/users/me", headers=auth, json={"nickname": f"E2E {STAMP}"})
    expect("PATCH /users/me", response, {200})

    response = call(client, "GET", "/dashboard", headers=auth)
    expect("GET /dashboard", response, {200})

    # --- problems ---------------------------------------------------------
    response = call(client, "GET", "/problems", headers=auth, params={"page": 1, "page_size": 5})
    expect("GET /problems", response, {200})
    problem_id = None
    if response.status_code == 200:
        items = response.json().get("items") or response.json().get("data") or []
        if items:
            problem_id = items[0].get("id")
    if problem_id:
        response = call(client, "GET", f"/problems/{problem_id}", headers=auth)
        expect("GET /problems/{id}", response, {200})
    else:
        record("GET /problems returned seeded problems", False, "no problems in list")

    # --- conversations ----------------------------------------------------
    response = call(client, "GET", "/conversations", headers=auth)
    expect("GET /conversations", response, {200})

    response = call(client, "POST", "/conversations", headers=auth, json={"title": "新对话", "mode": "normal"})
    expect("POST /conversations", response, {201})
    conversation_id = response.json().get("id") if response.status_code == 201 else None
    if not conversation_id:
        record("conversation created", False, "no conversation id")
        return

    response = call(client, "PATCH", f"/conversations/{conversation_id}", headers=auth, json={"title": "E2E 会话"})
    expect("PATCH /conversations/{id} title", response, {200})

    response = call(client, "PATCH", f"/conversations/{conversation_id}", headers=auth, json={"pinned": True})
    expect("PATCH /conversations/{id} pinned", response, {200})
    if response.status_code == 200:
        record("pinned flag persisted", response.json().get("pinned") is True, f"pinned={response.json().get('pinned')}")

    response = call(client, "PATCH", f"/conversations/{conversation_id}", headers=auth, json={})
    expect("PATCH /conversations/{id} empty body rejected", response, {422})

    # stream a normal chat message
    status, events = read_sse(client, f"/conversations/{conversation_id}/messages/stream", {"content": "用一句话解释二分查找", "mode": "normal"}, auth)
    names = event_names(events)
    record("POST stream returns HTTP 200", status == 200, f"status={status} events={names}")
    record("stream produced events", bool(names), f"{len(names)} events, last={names[-1] if names else None}")
    failed = [event for event in events if event["event"] == "run.failed"]
    record("stream did not fail", not failed, failed[0]["data"][:300] if failed else "")

    response = call(client, "GET", f"/conversations/{conversation_id}/messages", headers=auth, params={"page": 1, "page_size": 20})
    expect("GET /conversations/{id}/messages", response, {200})
    assistant_message_id = None
    user_message_id = None
    if response.status_code == 200:
        payload = response.json()
        items = payload.get("items", payload if isinstance(payload, list) else [])
        record("messages persisted", len(items) >= 2, f"{len(items)} messages")
        for item in items:
            if item.get("role") == "assistant" and assistant_message_id is None:
                assistant_message_id = item.get("id")
            if item.get("role") == "user" and user_message_id is None:
                user_message_id = item.get("id")
        record(
            "every message exposes retrieved_chunk_ids",
            bool(items) and all("retrieved_chunk_ids" in item for item in items),
            f"keys={sorted(items[0].keys()) if items else []}"[:300],
        )

    if assistant_message_id:
        response = call(client, "GET", f"/conversations/{conversation_id}/messages/{assistant_message_id}/citations", headers=auth)
        expect("GET message citations", response, {200})

    if user_message_id:
        response = call(client, "POST", f"/conversations/{conversation_id}/messages/{user_message_id}/retry", headers=auth, json={"content": "用一句话解释二分查找（重试）"})
        expect("POST message retry", response, {200, 202})

    response = call(client, "GET", f"/conversations/{conversation_id}/runs/active", headers=auth)
    expect("GET active run", response, {200})

    response = call(client, "POST", f"/conversations/{conversation_id}/run/stop", headers=auth)
    expect("POST run stop", response, {202, 404})

    # ACM analysis mode without problem should be rejected, with problem accepted
    status, events = read_sse(client, f"/conversations/{conversation_id}/messages/stream", {"content": "分析", "mode": "acm_analysis"}, auth)
    names = event_names(events)
    failed = [event for event in events if event["event"] == "run.failed"]
    record("acm_analysis without problem rejected", status != 200 or bool(failed), f"status={status} events={names}")

    if problem_id:
        status, events = read_sse(
            client,
            f"/conversations/{conversation_id}/messages/stream",
            {"content": "分析这道题的思路", "mode": "acm_analysis", "problem_id": problem_id},
            auth,
        )
        names = event_names(events)
        failed = [event for event in events if event["event"] == "run.failed"]
        record("acm_analysis with problem streamed", status == 200 and bool(names), f"events={names[:8]}")
        if failed:
            record("acm_analysis provider error", False, failed[0]["data"][:300])

    # --- knowledge base ---------------------------------------------------
    response = call(client, "GET", "/knowledge/groups", headers=auth)
    expect("GET /knowledge/groups", response, {200})

    response = call(client, "POST", "/knowledge/groups", headers=auth, json={"name": f"E2E 分组 {STAMP}"})
    expect("POST /knowledge/groups", response, {201})
    group_id = response.json().get("id") if response.status_code == 201 else None

    if group_id:
        response = call(client, "PATCH", f"/knowledge/groups/{group_id}", headers=auth, json={"name": f"E2E 分组改名 {STAMP}"})
        expect("PATCH /knowledge/groups/{id}", response, {200})

    response = call(client, "GET", "/knowledge/documents/policy", headers=auth)
    expect("GET /knowledge/documents/policy", response, {200})

    response = call(client, "GET", "/knowledge/documents", headers=auth)
    expect("GET /knowledge/documents", response, {200})

    document_id = None
    if group_id:
        content = "# 二分查找\n\n二分查找在有序数组中每次将搜索区间缩小一半，时间复杂度为 O(log n)。\n"
        files = {"file": ("e2e-note.md", content.encode("utf-8"), "text/markdown")}
        data = {"group_id": str(group_id), "title": "E2E 笔记"}
        response = call(client, "POST", "/knowledge/documents", headers=auth, files=files, data=data)
        expect("POST /knowledge/documents", response, {202})
        document_id = response.json().get("id") if response.status_code == 202 else None

    if document_id:
        final_status = None
        for _ in range(60):
            response = call(client, "GET", f"/knowledge/documents/{document_id}/status", headers=auth)
            if response.status_code != 200:
                break
            final_status = response.json().get("status")
            if final_status in {"indexed", "failed"}:
                break
            time.sleep(2)
        record("document indexed", final_status == "indexed", f"status={final_status}")

        response = call(client, "GET", f"/knowledge/documents/{document_id}/preview", headers=auth)
        expect("GET document preview", response, {200})

        response = call(client, "GET", f"/knowledge/documents/{document_id}/versions", headers=auth)
        expect("GET document versions", response, {200})

        response = call(client, "GET", f"/knowledge/documents/{document_id}/download", headers=auth)
        expect("GET document download url", response, {200})

    # RAG chat with knowledge scope
    status, events = read_sse(
        client,
        f"/conversations/{conversation_id}/messages/stream",
        {"content": "二分查找的时间复杂度是多少？", "mode": "normal", "knowledge_scope": "all"},
        auth,
    )
    names = event_names(events)
    record("knowledge_scope=all stream returns events", status == 200 and bool(names), f"events={names[:8]}")
    failed = [event for event in events if event["event"] == "run.failed"]
    if failed:
        record("knowledge_scope=all run failed", False, failed[0]["data"][:300])

    response = call(client, "POST", f"/conversations/{conversation_id}/messages/stream", headers=auth, json={"content": "hi", "knowledge_scope": "groups"})
    expect("knowledge_scope=groups without ids rejected", response, {422})

    # --- conversation bulk management -------------------------------------
    response = call(client, "POST", "/conversations/bulk", headers=auth, json={"conversation_ids": [conversation_id], "action": "pin"})
    expect("POST /conversations/bulk pin", response, {200, 202})

    response = call(client, "POST", "/conversations/bulk", headers=auth, json={"conversation_ids": [conversation_id], "action": "unpin"})
    expect("POST /conversations/bulk unpin", response, {200, 202})

    response = call(client, "POST", "/conversations/bulk", headers=auth, json={"conversation_ids": [], "action": "delete"})
    expect("POST /conversations/bulk empty rejected", response, {422})

    if document_id:
        response = call(client, "POST", f"/knowledge/documents/{document_id}/reindex", headers=auth)
        expect("POST document reindex", response, {202})

    response = call(client, "POST", "/conversations/bulk", headers=auth, json={"conversation_ids": [conversation_id], "action": "delete"})
    expect("POST /conversations/bulk delete", response, {200, 202})

    response = call(client, "GET", f"/conversations/{conversation_id}", headers=auth)
    expect("deleted conversation gone", response, {404})

    if document_id:
        response = call(client, "DELETE", f"/knowledge/documents/{document_id}", headers=auth)
        expect("DELETE knowledge document", response, {204})
    if group_id:
        response = call(client, "DELETE", f"/knowledge/groups/{group_id}", headers=auth)
        expect("DELETE knowledge group", response, {204})

    response = call(client, "POST", "/auth/logout", json={"refresh_token": refresh})
    expect("POST /auth/logout", response, {204, 200})

    client.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        failures.append(("unhandled exception", traceback.format_exc()[-500:]))
    print("\n=== SUMMARY ===")
    print(f"checks={len(checks)} failed={len(failures)}")
    for name, detail in failures:
        print(f"FAILED: {name} :: {detail}"[:500])
    sys.exit(1 if failures else 0)
