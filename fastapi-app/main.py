from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
# 2. Loki 로그 핸들러 설정
# getenv를 통해 Docker Compose에 설정된 LOKI_ENDPOINT를 가져옵니다.
loki_url = getenv("LOKI_ENDPOINT", "http://loki:3100/loki/api/v1/push")

loki_logs_handler = LokiQueueHandler(
    Queue(-1),
    url=loki_url,
    tags={"application": "fastapi"},
    version="1",
)

# 3. 커스텀 액세스 로거 설정
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)
custom_logger.addHandler(loki_logs_handler)

# --- 미들웨어 설정 (로그 수집의 핵심) ---

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    모든 HTTP 요청을 가로채서 응답 시간과 상태 코드를 계산하고
    그 결과를 Loki 핸들러가 연결된 로거로 전송합니다.
    """
    start_time = time.time()
    
    # 다음 프로세스(엔드포인트 함수) 실행
    response = await call_next(request)
    
    # 응답 시간 계산
    duration = time.time() - start_time

    # 로그 메시지 포맷 구성 (IP - "METHOD PATH HTTP" STATUS DURATION)
    log_message = (
        f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" '
        f'{response.status_code} {duration:.3f}s'
    )

    # Loki로 로그 전송
    custom_logger.info(log_message)

    return response
    
JSON_FILE = "todo.json"

#@app.get('/')
#async def welcome() -> dict:
#v    return {"message": "Hello world"}

@app.get("/")
def read_index():
    return FileResponse("templates/index.html")

@app.get("/index.html")
def read_index_html():
    return FileResponse("templates/index.html")

class TodoItem(BaseModel):
    id : int
    title : str
    content : str
    completed : bool
    due_date : Optional[str] = None

todolists = []

#create read update delete

@app.get("/todos", response_model=list[TodoItem])
def read():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        todolists = json.load(f)
        return todolists

@app.post("/todos", response_model=TodoItem)
def create(todolist : TodoItem):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        todolists = json.load(f)

    new_id = max([item["id"] for item in todolists], default=0) + 1

    new_todo = {
        "id": new_id,
        "title": todolist.title,
        "content": todolist.content,
        "completed": todolist.completed,
        "due_date": todolist.due_date
    }

    todolists.append(new_todo)
    
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(todolists, f, ensure_ascii=False, indent=4)
    return todolist

@app.put("/todos/{todo_id}", response_model=TodoItem, responses={404: {"description": "List not found"}})
def update(todo_id: int, todolist : TodoItem):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        todolists = json.load(f)
    
    found = False
    for i, item in enumerate(todolists):
        if item["id"] == todo_id:
            todolists[i] = todolist.model_dump()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="List not found")

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(todolists, f, indent=4)
    return todolist
    

@app.delete("/todos/{todo_id}", response_model=dict, responses={404: {"description": "List not found"}})
def delete(todo_id: int):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        todolists = json.load(f)

    deleted_item = None
    for i, item in enumerate(todolists):
        if item["id"] == todo_id:
            deleted_item = todolists.pop(i)
            break

    if deleted_item is None:
        raise HTTPException(status_code=404, detail="List not found")

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(todolists, f, indent=4)

    return deleted_item
