import requests

BASE_URL = "http://163.239.77.78:8002"

def test_live_get_todos():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200

def test_live_create_todo():
    todo = {
        "id": 1,
        "title": "Live Test",
        "content": "Testing deployed API",
        "completed": False
    }
    response = requests.post(f"{BASE_URL}/todos", json=todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Live Test"
    assert response.json()["content"] == "Testing deployed API"
    assert response.json()["completed"] is False

def test_live_update_todo():
    updated_todo = {
        "id": 1,
        "title": "Live Updated",
        "content": "Updated deployed API",
        "completed": True
    }
    response = requests.put(f"{BASE_URL}/todos/1", json=updated_todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Live Updated"
    assert response.json()["content"] == "Updated deployed API"
    assert response.json()["completed"] is True

def test_live_delete_todo():
    response = requests.delete(f"{BASE_URL}/todos/1")
    assert response.status_code in [200, 500]