"""
Session management endpoints.
Handles starting learning sessions and initial questionnaire delivery.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid

from ..models.schemas import (
    StartSessionRequest, StartSessionResponse, HealthResponse
)
from ..models.database import get_db, Session as DBSession
from ..services.questionnaire import questionnaire_service
from ..config import settings
from .. import __version__

router = APIRouter(prefix="/api/v1", tags=["Sessions"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API health status.
    
    Returns:
        HealthResponse with status and version information.
    """
    return HealthResponse(
        status="healthy",
        version=__version__
    )


@router.get("/skills")
async def list_available_skills():
    """
    Get list of available skills with configuration.
    
    Returns:
        List of skill names that have questionnaire/quiz configurations.
    """
    skills = questionnaire_service.get_available_skills()
    return {
        "skills": skills,
        "total": len(skills),
        "note": "You can also request any skill name; generic questionnaires will be generated."
    }


@router.post("/sessions/start", response_model=StartSessionResponse)
async def start_learning_session(
    request: StartSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new learning session for a specified skill.
    
    This endpoint:
    1. Creates a new session with unique ID
    2. Generates a questionnaire tailored to the skill
    3. Returns both for the learner to complete
    
    Args:
        request: Contains the skill the user wants to learn
    
    Returns:
        StartSessionResponse with session_id and questionnaire
    
    Example:
        POST /api/v1/sessions/start
        {
            "skill": "Python programming"
        }
    """
    # Generate questionnaire
    questionnaire = questionnaire_service.generate_questionnaire(request.skill)
    
    # Create session
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=settings.session_expiry_hours)
    
    db_session = DBSession(
        id=session_id,
        skill=request.skill,
        expires_at=expires_at
    )
    
    db.add(db_session)
    await db.flush()
    
    return StartSessionResponse(
        session_id=session_id,
        skill=request.skill,
        questionnaire=questionnaire,
        created_at=datetime.utcnow()
    )


@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current status of a learning session.
    
    Returns:
        Session details including assigned level and progress.
    """
    from sqlalchemy import select
    
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    return {
        "session_id": session.id,
        "skill": session.skill,
        "assigned_level": session.assigned_level,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "questionnaire_completed": session.questionnaire_responses is not None,
        "level_confidence": session.level_confidence
    }
