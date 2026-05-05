from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict
import json
import os
from prometheus_fastapi_instrumentator import Instrumentator
import subprocess  # 보안 이슈용
import hashlib        # [추가] 보안 이슈용
import random         # [추가] 보안 이슈용
import logging        # [추가] print 대체 비교용

app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

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
        "completed": todolist.completed
    }

    todolists.append(new_todo)

    print("Todo created")  # Rule 선택 고민: print 사용
    
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


# 1. 가벼운 Code Smell

unused_variable = 123                          # [기존유지] Code Smell: 사용되지 않는 변수 (sonar:S1481)

x = None
if x == None:                                  # [추가] Code Smell: == None 대신 is None 써야 함 (sonar:S5727)
    pass

my_list = []
if len(my_list) == 0:                          # [추가] Code Smell: len() == 0 대신 not my_list 권장 (sonar:S1244)
    pass

# TODO: 나중에 알림 기능 추가                   # [추가] Code Smell: TODO 주석 방치 (sonar:S1135)

def say_hello():
    print("Hello")                             # [기존유지] Code Smell: print 사용 (룰 선택 고민 케이스와 중복 의도)


# 2. 중간 난이도 Bug

def check_duplicate(a, b):
    if a == a:                                 # [추가] Bug: 동일 변수 비교 실수 (sonar:S1764), a==b 의도
        return True
    return b

def get_user(user_id: int):
    user = {"id": user_id}
    return                                     # [추가] Bug: 값 없는 return, dead code 유발 (sonar:S1763)
    return user

def risky_read():
    try:
        with open("nonexistent.txt") as f:
            return f.read()
    except:                                    # [추가] Bug: 빈 except, 예외 무시 (sonar:S110535)
        pass

def get_title(todo):
    return todo["title"]                       # [기존유지] Bug: None 체크 없이 dict 접근


# 3. 구조 / 리팩토링

def complex_function(x):                       # [기존유지] Cognitive Complexity 초과 (sonar:S3776)
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    return "big"
    return "small"

def grade(score):                              # [추가] 과도한 반환 경로 (sonar:S1776) - 리팩토링 필요하나 의도가 명확한 케이스
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    if score >= 50:
        return "E"
    return "F"

def create_report(title, author, date,         # [추가] 파라미터 과다 (sonar:S107) - 구조 개선 필요
                  content, category, tags,
                  version, is_public,
                  reviewer, deadline):
    pass

# 4. 보안 이슈

HARDCODED_PASSWORD = "super_secret_1234"       # [기존유지→강화] Security Hotspot: 하드코딩 패스워드 (sonar:S2068)

def dangerous_function(user_input: str):
    return subprocess.check_output(            # [기존유지] Vulnerability: shell=True Command Injection (sonar:S607)
        user_input, shell=True
    )

def hash_password(password: str):
    return hashlib.md5(                        # [추가] Vulnerability: MD5는 암호학적으로 취약 (sonar:S4790)
        password.encode()
    ).hexdigest()

def generate_token():
    return random.randint(100000, 999999)      # [추가] Vulnerability: 암호학적으로 안전하지 않은 난수 (sonar:S2245)

# 5. Rule 선택 / 제외 고민되는 케이스 (Quality Profile용)

# 고민 케이스 A: print vs logging
# → 프로덕션에선 logging이 맞지만, 개발/디버그 중엔 print도 허용할지 팀 결정 필요
def debug_create(item):
    print(f"Creating item: {item}")            # [추가] print 사용 - Rule 활성화 여부 팀 판단 케이스
    logging.info(f"Creating item: {item}")     # 올바른 방식

# 고민 케이스 B: 중복 엔드포인트
# → /와 /index.html이 같은 파일 반환 - SonarQube는 잡지 못하지만 설계 냄새
# → "SonarQube가 못 잡는 이슈도 있다"는 발표 포인트로 활용

# 고민 케이스 C: type hint 없는 함수
def process(data):                             # [추가] type hint 없음 - 팀 컨벤션에 따라 Rule 활성화 고민
    return data

# 고민 케이스 D: magic number
def calculate_discount(price):
    return price * 0.85                        # [추가] Magic Number (sonar:S109) - 상수로 분리할지 팀 판단
