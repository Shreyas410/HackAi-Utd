"""
Data privacy and ethics endpoints.
Handles data deletion, transparency, and user rights.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime

from ..models.schemas import (
    DeleteDataRequest, DeleteDataResponse,
    ChallengeAssessmentRequest, ChallengeAssessmentResponse,
    SkillLevel
)
from ..models.database import get_db, Session as DBSession, Quiz, ScenarioAttempt

router = APIRouter(prefix="/api/v1/privacy", tags=["Privacy"])


@router.delete("/data", response_model=DeleteDataResponse)
async def delete_user_data(
    request: DeleteDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all data associated with a session.
    
    This endpoint complies with data privacy best practices by allowing
    users to completely remove their data from the system.
    
    Args:
        request: Session ID and confirmation flag
    
    Returns:
        DeleteDataResponse confirming deletion
    
    Example:
        DELETE /api/v1/privacy/data
        {
            "session_id": "abc-123",
            "confirmation": true
        }
    """
    if not request.confirmation:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires explicit confirmation. Set 'confirmation' to true."
        )
    
    # Get session
    result = await db.execute(
        select(DBSession).where(DBSession.id == request.session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        return DeleteDataResponse(
            success=True,
            message="Data was already deleted",
            deleted_at=session.deleted_at or datetime.utcnow()
        )
    
    # Delete associated quizzes
    await db.execute(
        delete(Quiz).where(Quiz.session_id == request.session_id)
    )
    
    # Delete scenario attempts
    await db.execute(
        delete(ScenarioAttempt).where(ScenarioAttempt.session_id == request.session_id)
    )
    
    # Clear session data (keep record for audit but remove PII)
    session.job_title = None
    session.experience_years = None
    session.prior_exposure = None
    session.learning_goals = None
    session.preferred_modalities = None
    session.questionnaire_responses = None
    session.self_ratings = None
    session.classification_factors = None
    session.data_deleted = True
    session.deleted_at = datetime.utcnow()
    
    await db.flush()
    
    return DeleteDataResponse(
        success=True,
        message="All personal data has been deleted. Session record retained for audit purposes only.",
        deleted_at=session.deleted_at
    )


@router.post("/challenge-level", response_model=ChallengeAssessmentResponse)
async def challenge_assessment(
    request: ChallengeAssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Challenge the assigned skill level.
    
    Users have the right to challenge their assessment. This endpoint
    allows requesting a different level, which may require an additional quiz.
    
    Args:
        request: Session ID, requested level, and optional reason
    
    Returns:
        ChallengeAssessmentResponse with decision
    
    Example:
        POST /api/v1/privacy/challenge-level
        {
            "session_id": "abc-123",
            "requested_level": "intermediate",
            "reason": "I have more experience than the quiz showed"
        }
    """
    # Get session
    result = await db.execute(
        select(DBSession).where(DBSession.id == request.session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    if not session.assigned_level:
        raise HTTPException(
            status_code=400,
            detail="No level has been assigned yet. Complete the questionnaire first."
        )
    
    current_level = SkillLevel(session.assigned_level)
    requested_level = request.requested_level
    
    # Same level - no change needed
    if current_level == requested_level:
        return ChallengeAssessmentResponse(
            session_id=request.session_id,
            challenge_accepted=True,
            new_level=current_level,
            additional_quiz_required=False,
            message="Your current level matches your request. No change needed."
        )
    
    # Requesting lower level - typically accepted
    level_order = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED]
    current_idx = level_order.index(current_level)
    requested_idx = level_order.index(requested_level)
    
    if requested_idx < current_idx:
        # Accepting lower level
        session.assigned_level = requested_level.value
        await db.flush()
        
        return ChallengeAssessmentResponse(
            session_id=request.session_id,
            challenge_accepted=True,
            new_level=requested_level,
            additional_quiz_required=False,
            message=f"Level changed to {requested_level.value}. You can always retake the quiz to reassess."
        )
    
    # Requesting higher level - requires additional quiz
    return ChallengeAssessmentResponse(
        session_id=request.session_id,
        challenge_accepted=False,
        new_level=None,
        additional_quiz_required=True,
        message=f"To move to {requested_level.value}, please complete an additional diagnostic quiz at that level. Use GET /api/v1/quiz/{request.session_id} to start."
    )


@router.get("/data-policy")
async def get_data_policy():
    """
    Get information about data collection and usage policies.
    
    Returns:
        Data policy information for transparency.
    """
    return {
        "title": "Data Privacy Policy",
        "last_updated": "2024-01-15",
        "data_collected": {
            "questionnaire_responses": {
                "description": "Your answers to the skill assessment questionnaire",
                "purpose": "To determine appropriate learning content",
                "retention": "Until you delete your session or it expires"
            },
            "quiz_responses": {
                "description": "Your answers to diagnostic quizzes",
                "purpose": "To assess and refine your skill level",
                "retention": "Until you delete your session or it expires"
            },
            "practice_activity": {
                "description": "Your choices in practice scenarios",
                "purpose": "To track progress and provide feedback",
                "retention": "Until you delete your session or it expires"
            }
        },
        "data_not_collected": [
            "Real name or identity information",
            "Health information",
            "Race, ethnicity, or religion",
            "Financial information",
            "Location data beyond session info"
        ],
        "data_usage": [
            "Personalizing learning content to your level",
            "Recommending appropriate resources",
            "Improving the learning system (aggregated, anonymized)"
        ],
        "your_rights": {
            "access": "View all data associated with your session via /api/v1/sessions/{session_id}",
            "deletion": "Delete all your data via DELETE /api/v1/privacy/data",
            "challenge": "Challenge your assessed level via POST /api/v1/privacy/challenge-level",
            "transparency": "Understand how your level was determined via /api/v1/questionnaire/classification-explanation"
        },
        "data_security": {
            "storage": "Data is stored in a secure database",
            "encryption": "Sensitive data is encrypted at rest",
            "access": "Access is limited to authenticated API endpoints"
        },
        "session_expiry": "Sessions expire after 24 hours of inactivity",
        "contact": "For privacy concerns, contact the system administrator"
    }
