"""
Playwright 기반 UI 테스트 — FastAPI To-Do 앱
실행:
    pytest tests/test_ui_playwright.py -v --html=reports/ui_report.html --self-contained-html
Jenkins headless:
    PLAYWRIGHT_BROWSERS_PATH=0 pytest tests/test_ui_playwright.py -v
"""

import json
import os
import sys
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import sync_playwright

# ── 경로 설정: fastapi-app/ 를 루트로 인식 ──────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app  # noqa: E402

# ── 상수 ──────────────────────────────────────────────────────────
_PORT = 18765
BASE_URL = f"http://127.0.0.1:{_PORT}"
JSON_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "todo.json"))


# ── 유틸 ──────────────────────────────────────────────────────────

def _write_json(data: list) -> None:
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ── 서버 스레드 ───────────────────────────────────────────────────

class _UvicornThread(threading.Thread):
    """데몬 스레드로 uvicorn 서버를 실행한다."""

    def __init__(self, port: int) -> None:
        super().__init__(daemon=True)
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        self.server = uvicorn.Server(config)

    def run(self) -> None:
        self.server.run()

    def stop(self) -> None:
        self.server.should_exit = True


# ── pytest fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def live_server():
    """세션 전체에서 한 번 서버를 기동한다."""
    thread = _UvicornThread(_PORT)
    thread.start()
    time.sleep(1.5)          # 서버 바인딩 대기
    yield BASE_URL
    thread.stop()
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser(live_server):
    """세션 범위의 Chromium 브라우저 인스턴스 (headless)."""
    with sync_playwright() as pw:
        b = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",               # Jenkins/Docker 환경
                "--disable-dev-shm-usage",    # 공유메모리 부족 방지
            ],
        )
        yield b
        b.close()


@pytest.fixture(autouse=True)
def reset_todos():
    """각 테스트 전·후로 todo.json 을 초기화한다."""
    _write_json([])
    yield
    _write_json([])


@pytest.fixture
def page(browser, live_server, reset_todos):
    """테스트마다 새 컨텍스트와 페이지를 열고 / 로 이동한다.
    reset_todos 에 명시적으로 의존해 JSON 초기화가 먼저 완료되도록 보장한다.
    """
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(live_server, wait_until="networkidle")
    yield pg
    ctx.close()


# ── UI 헬퍼 ──────────────────────────────────────────────────────

def _add_todo(page, title: str, content: str) -> None:
    """폼을 통해 투두를 추가하고, 목록이 늘어날 때까지 기다린다."""
    before = page.locator("#todo-list li").count()
    page.fill("#title", title)
    page.fill("#content", content)
    page.click("button[type='submit']")
    # 항목 수가 before 보다 커질 때까지 대기 (타임아웃 5 s)
    page.wait_for_function(
        "(count) => document.querySelectorAll('#todo-list li').length > count",
        arg=before,
        timeout=5_000,
    )


# ── 테스트 케이스 ─────────────────────────────────────────────────

class TestPageLoad:
    """페이지 기본 렌더링 검증"""

    def test_title(self, page):
        assert page.title() == "To-Do List"

    def test_heading_visible(self, page):
        assert page.locator("h1").inner_text() == "To-Do List"

    def test_form_elements_visible(self, page):
        assert page.is_visible("#todo-form")
        assert page.is_visible("#title")
        assert page.is_visible("#content")
        assert page.is_visible("button[type='submit']")

    def test_todo_list_initially_empty(self, page):
        assert page.locator("#todo-list li").count() == 0


class TestCreateTodo:
    """투두 생성 UI 검증"""

    def test_create_single_todo(self, page):
        _add_todo(page, "Buy milk", "Get 2 liters from the store")

        items = page.locator("#todo-list li")
        assert items.count() == 1

        text = items.first.inner_text()
        assert "Buy milk" in text
        assert "Get 2 liters from the store" in text

    def test_completed_flag_defaults_to_false(self, page):
        _add_todo(page, "New task", "Some content")

        text = page.locator("#todo-list li").first.inner_text()
        # index.html: `(Completed: ${todo.completed})` → false
        assert "Completed: false" in text

    def test_create_multiple_todos(self, page):
        _add_todo(page, "Task Alpha", "Content A")
        _add_todo(page, "Task Beta", "Content B")

        items = page.locator("#todo-list li")
        assert items.count() == 2

    def test_form_fields_cleared_after_submit(self, page):
        _add_todo(page, "Clearance check", "Any content")

        assert page.input_value("#title") == ""
        assert page.input_value("#content") == ""


class TestListTodos:
    """목록 표시 검증"""

    def test_existing_todos_shown_on_load(self, page):
        """JSON 에 미리 저장된 항목이 페이지 로드 시 표시된다."""
        _write_json([
            {"id": 1, "title": "Task A", "content": "Alpha content", "completed": False},
            {"id": 2, "title": "Task B", "content": "Beta content",  "completed": True},
        ])
        page.reload(wait_until="networkidle")

        items = page.locator("#todo-list li")
        assert items.count() == 2

        texts = [items.nth(i).inner_text() for i in range(2)]
        assert any("Task A" in t and "Alpha content" in t for t in texts)
        assert any("Task B" in t and "Beta content"  in t for t in texts)

    def test_completed_true_displayed_correctly(self, page):
        _write_json([
            {"id": 1, "title": "Done task", "content": "Finished", "completed": True},
        ])
        page.reload(wait_until="networkidle")

        text = page.locator("#todo-list li").first.inner_text()
        assert "Completed: true" in text

    def test_each_item_has_edit_and_delete_buttons(self, page):
        _add_todo(page, "Button check", "Has buttons")

        li = page.locator("#todo-list li").first
        assert li.locator("button", has_text="Edit").count() == 1
        assert li.locator("button", has_text="Delete").count() == 1


class TestDeleteTodo:
    """투두 삭제 UI 검증"""

    def test_delete_only_item(self, page):
        _add_todo(page, "Delete me", "This will be removed")
        assert page.locator("#todo-list li").count() == 1

        page.locator("#todo-list li").first.locator("button", has_text="Delete").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#todo-list li').length === 0",
            timeout=5_000,
        )

        assert page.locator("#todo-list li").count() == 0

    def test_delete_first_of_two_leaves_second(self, page):
        _add_todo(page, "First task",  "First content")
        _add_todo(page, "Second task", "Second content")

        page.locator("#todo-list li").first.locator("button", has_text="Delete").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#todo-list li').length === 1",
            timeout=5_000,
        )

        remaining = page.locator("#todo-list li").first.inner_text()
        assert "Second task" in remaining
        assert "First task" not in remaining

    def test_delete_does_not_affect_other_items(self, page):
        _write_json([
            {"id": 1, "title": "Keep this",   "content": "Stays",   "completed": False},
            {"id": 2, "title": "Remove this", "content": "Deleted", "completed": False},
        ])
        page.reload(wait_until="networkidle")

        # 'Remove this' 항목의 Delete 클릭
        target = page.locator("#todo-list li").filter(has_text="Remove this")
        target.locator("button", has_text="Delete").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#todo-list li').length === 1",
            timeout=5_000,
        )

        remaining = page.locator("#todo-list li").first.inner_text()
        assert "Keep this" in remaining
        assert "Remove this" not in remaining
