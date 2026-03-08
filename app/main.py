"""
Personalised Learning System API
Main FastAPI application entry point.

This API provides endpoints for:
- Starting learning sessions and generating questionnaires
- Classifying learner skill levels (Beginner/Intermediate/Advanced)
- Generating and scoring diagnostic quizzes
- Scenario-based practice with branching logic
- Concept map visualization
- Course and resource recommendations (YouTube, Coursera, Udemy)
- Data privacy and user rights
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .models.database import init_db
from .routers import (
    sessions_router,
    questionnaire_router,
    quiz_router,
    practice_router,
    concept_map_router,
    resources_router,
    privacy_router
)
from . import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup
    await init_db()
    print(f"Database initialized")
    print(f"Learning System API v{__version__} started")
    
    yield
    
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Personalised Learning System API",
    description="""
## Overview

A back-end API for an adaptive learning system that assesses learner skill levels 
and provides personalized content recommendations.

## Features

### 🎯 Skill Assessment
- Dynamic questionnaire generation based on chosen skill
- Multi-factor level classification (Beginner/Intermediate/Advanced)
- Based on the Dreyfus Model of Skill Acquisition

### 📝 Diagnostic Quizzes
- Level-appropriate quiz generation
- Automatic scoring with potential level adjustment
- Support for multiple question types

### 🎮 Scenario-Based Practice
- Realistic practice scenarios with branching logic
- Decision points with consequences and feedback
- Progress tracking

### 🗺️ Concept Maps
- Visual representation of skill topics
- Shows relationships between concepts
- Indicates difficulty levels

### 📚 Resource Recommendations
- Personalized recommendations from YouTube, Coursera, and Udemy
- Filtered by level, modality, duration, and cost
- YouTube embed links with time-based snippets

### 🔒 Privacy & Ethics
- No sensitive personal data collected
- User data deletion support
- Transparent classification explanation
- Right to challenge assessments

## Getting Started

1. **Start a Session**: POST /api/v1/sessions/start with your chosen skill
2. **Complete Questionnaire**: Submit responses to receive your skill level
3. **Take Quiz**: Optional diagnostic quiz to refine level
4. **Practice**: Work through scenarios to apply learning
5. **Get Resources**: Receive personalized course recommendations

## Authentication

Currently, the API uses session-based access without authentication.
Each session has a unique ID that should be kept private.
""",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions_router)
app.include_router(questionnaire_router)
app.include_router(quiz_router)
app.include_router(practice_router)
app.include_router(concept_map_router)
app.include_router(resources_router)
app.include_router(privacy_router)


@app.get("/", tags=["Root"])
async def root():
    """
    API root endpoint with navigation links.
    """
    return {
        "name": "Personalised Learning System API",
        "version": __version__,
        "documentation": "/docs",
        "openapi_spec": "/openapi.json",
        "endpoints": {
            "health": "/api/v1/health",
            "skills": "/api/v1/skills",
            "sessions": "/api/v1/sessions/start",
            "questionnaire": "/api/v1/questionnaire/submit",
            "quiz": "/api/v1/quiz/{session_id}",
            "practice": "/api/v1/practice/{session_id}/start",
            "concept_map": "/api/v1/concept-map/{skill}",
            "resources": "/api/v1/resources/{session_id}",
            "privacy": "/api/v1/privacy/data-policy"
        }
    }


def custom_openapi():
    """Generate custom OpenAPI schema with additional documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Personalised Learning System API",
        version=__version__,
        description=app.description,
        routes=app.routes,
    )
    
    # Add additional schema info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Sessions",
            "description": "Start learning sessions and manage session state"
        },
        {
            "name": "Questionnaire",
            "description": "Submit questionnaire responses and receive skill level classification"
        },
        {
            "name": "Quiz",
            "description": "Diagnostic quizzes tailored to learner level"
        },
        {
            "name": "Practice",
            "description": "Scenario-based practice with branching logic"
        },
        {
            "name": "Concept Map",
            "description": "Visual concept maps showing topic relationships"
        },
        {
            "name": "Resources",
            "description": "Course and video recommendations from YouTube, Coursera, and Udemy"
        },
        {
            "name": "Privacy",
            "description": "Data privacy, deletion, and user rights"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Mount static files for frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    
    @app.get("/app", include_in_schema=False)
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
