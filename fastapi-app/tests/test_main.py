import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from main import app, TodoItem

client = TestClient(app, raise_server_exceptions=False)

JSON_FILE = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), "todo.json")

def write_todos(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    write_todos([])
    yield
    write_todos([])

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_todos_with_items():
    todo = TodoItem(id=1, title="Test", content="Test content", completed=False)
    write_todos([todo.model_dump()])
    response = client.get("/todos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test"
    assert response.json()[0]["content"] == "Test content"

def test_create_todo():
    todo = {"id": 1, "title": "Test", "content": "Test content", "completed": False}
    response = client.post("/todos", json=todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Test"
    assert response.json()["content"] == "Test content"
    assert response.json()["completed"] is False

def test_create_todo_invalid():
    todo = {"id": 1, "title": "Test"}
    response = client.post("/todos", json=todo)
    assert response.status_code == 422

def test_update_todo():
    todo = TodoItem(id=1, title="Test", content="Test content", completed=False)
    write_todos([todo.model_dump()])
    updated_todo = {"id": 1, "title": "Updated", "content": "Updated content", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["content"] == "Updated content"
    assert response.json()["completed"] is True

def test_update_todo_not_found():
    updated_todo = {"id": 1, "title": "Updated", "content": "Updated content", "completed": True}
    response = client.put("/todos/1", json=updated_todo)
    assert response.status_code == 404
    assert response.json()["detail"] == "List not found"

def test_delete_todo():
    todo = TodoItem(id=1, title="Test", content="Test content", completed=False)
    write_todos([todo.model_dump()])
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["title"] == "Test"
    assert response.json()["content"] == "Test content"

def test_delete_todo_not_found():
    response = client.delete("/todos/1")
    assert response.status_code == 404
    assert response.json()["detail"] == "List not found"