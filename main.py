from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import io
import PyPDF2
import docx
from db_connect import create_user, verify_user, UserSignup, save_user_profile, get_user_profile, UserProfile
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

class CareerRoadmapRequest(BaseModel):
    resume_text: str
    target_role: str

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

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    text = ""
    try:
        if filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            text = file_content.decode('utf-8')
    except Exception as e:
        print(f"Error extracting text: {e}")
    return text

@app.post("/api/career-trajectory/analyze-resume")
async def api_career_trajectory_analyze_resume(
    resume: UploadFile = File(...),
    user_id: str = Form(None)
):
    content = await resume.read()
    text = extract_text_from_file(content, resume.filename)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file.")
    
    result = ai_service.analyze_resume(text)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # If the user is logged in, extract profile data and save it
    if user_id and "profile" in result:
        profile_data = result["profile"]
        profile_data["resume_text"] = text
        success, msg = save_user_profile(user_id, profile_data)
        if not success:
            print(f"Warning: Failed to save profile: {msg}")

    return {"extracted_text": text, "analysis": result}

@app.get("/api/profile/{user_id}")
async def api_get_profile(user_id: str):
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.put("/api/profile")
async def api_update_profile(profile: UserProfile):
    success, msg = save_user_profile(profile.user_id, profile.model_dump())
    if success:
        return {"success": True, "message": msg}
    else:
        raise HTTPException(status_code=500, detail=msg)

@app.post("/api/career-trajectory/roadmap")
async def api_career_trajectory_roadmap(request: CareerRoadmapRequest):
    result = ai_service.generate_roadmap(request.resume_text, request.target_role)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

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
