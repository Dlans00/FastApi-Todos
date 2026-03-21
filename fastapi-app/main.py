from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from typing import List, Dict
import json
import os

app = FastAPI()

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
    
    todolists.append(todolist.model_dump())

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(todolists, f, ensure_ascii=False, indent=4)
    return todolist

@app.put("/todos/{todo_id}", response_model=TodoItem)
def update(todo_id: int, todolist : TodoItem):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        todolists = json.load(f)
    
    try:
        #todolists[todo_id] = todolist.model_dump()
        for i, item in enumerate(todolists):
            if item["id"] == todo_id:
                todolists[i] = todolist.model_dump()

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(todolists, f, indent=4)
        return todolist
    
    except IndexError:
        raise HTTPException(status_code=404, detail="List not found")

@app.delete("/todos/{todo_id}", response_model=dict)
def delete(todo_id: int):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        todolists = json.load(f)
    
    try:
        #todolist = todolists.pop(todo_id)
        for i, item in enumerate(todolists):
            if item["id"] == todo_id:
                deleted_item = todolists.pop(i)
        
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(todolists, f, indent=4)
        return deleted_item
    
    except IndexError:
        raise HTTPException(status_code=404, detail="List not found")
