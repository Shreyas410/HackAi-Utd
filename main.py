from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from db_connect import create_user, verify_user, UserSignup
import ai_service

app = FastAPI(title="LearnPath API")

# Define request models
class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QuickLearnStartRequest(BaseModel):
    topic: str
    time_limit_minutes: int

class QuickLearnChatRequest(BaseModel):
    topic: str
    content: str
    question: str
    history: List[Dict[str, str]]

class QuickLearnQuizRequest(BaseModel):
    topic: str
    content: str
    history: List[Dict[str, str]]

class QuickLearnSubmitRequest(BaseModel):
    user_answers: Dict[str, str]
    quiz_data: List[Dict[str, Any]]

@app.post("/api/signup")
async def api_signup(request: SignupRequest):
    success, message = create_user(request.email, request.password)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post("/api/login")
async def api_login(request: LoginRequest):
    success, message_or_user = verify_user(request.email, request.password)
    if success:
        user_id = message_or_user
        # In a real app, generate a JWT token here. Returning user_id for simplicity as demo.
        return {"success": True, "token": user_id, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail=message_or_user)

# --- Quick Learner Endpoints ---

@app.post("/api/quick-learn/start")
async def api_quick_learn_start(request: QuickLearnStartRequest):
    content = ai_service.generate_quick_content(request.topic, request.time_limit_minutes)
    if "Error" in content and len(content) < 150:
         raise HTTPException(status_code=500, detail="Failed to generate content")
    return {"content": content}

@app.post("/api/quick-learn/chat")
async def api_quick_learn_chat(request: QuickLearnChatRequest):
    answer = ai_service.answer_followup(request.content, request.question, request.history)
    return {"answer": answer}

@app.post("/api/quick-learn/quiz")
async def api_quick_learn_quiz(request: QuickLearnQuizRequest):
    quiz = ai_service.generate_quiz(request.topic, request.content, request.history)
    return {"quiz": quiz}

@app.post("/api/quick-learn/submit")
async def api_quick_learn_submit(request: QuickLearnSubmitRequest):
    report = ai_service.evaluate_quiz(request.user_answers, request.quiz_data)
    return {"report": report}

# Serve frontend static files
# Get the absolute path to the frontend directory
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/{path:path}")
async def catch_all(path: str):
    file_path = os.path.join(frontend_dir, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
