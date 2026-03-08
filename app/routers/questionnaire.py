"""
Questionnaire submission and level classification endpoints.
Classification is performed by Gemini API based on the Dreyfus model.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..models.schemas import (
    SubmitQuestionnaireRequest, SubmitQuestionnaireResponse,
    QuestionnaireAnswer, SkillLevel
)
from ..models.database import get_db, Session as DBSession
from ..services.classification import classification_service
from ..config import settings

router = APIRouter(prefix="/api/v1/questionnaire", tags=["Questionnaire"])


@router.post("/submit", response_model=SubmitQuestionnaireResponse)
async def submit_questionnaire(
    request: SubmitQuestionnaireRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit questionnaire responses and receive skill level classification from Gemini.
    
    This endpoint:
    1. Validates the session exists
    2. Stores the questionnaire responses
    3. Sends responses to Gemini API for classification
    4. Returns the Gemini-assigned level with explanation
    
    IMPORTANT: Classification is performed entirely by Gemini API.
    No local threshold logic is applied - Gemini's response is used directly.
    
    Args:
        request: Session ID and list of answers
    
    Returns:
        SubmitQuestionnaireResponse with assigned level and Gemini's explanation
    
    Classification uses the Dreyfus model (via Gemini):
    - Beginner (Novice/Advanced Beginner): Little experience, relies on explicit rules
    - Intermediate (Competent): Some experience, can apply rules in context
    - Advanced (Proficient/Expert): Extensive experience, uses intuition
    
    Example:
        POST /api/v1/questionnaire/submit
        {
            "session_id": "abc-123",
            "answers": [
                {"question_id": "job_title", "answer": "Software Developer"},
                {"question_id": "self_rating_syntax", "answer": "4"}
            ]
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
    
    # Convert answers to dict for storage
    answers_dict = {a.question_id: a.answer for a in request.answers}
    
    # Store responses
    session.questionnaire_responses = answers_dict
    
    # Extract and store self-ratings separately
    self_ratings = {}
    for key, value in answers_dict.items():
        if key.startswith("self_rating_"):
            self_ratings[key] = value
    session.self_ratings = self_ratings
    
    # Store other profile data
    session.job_title = answers_dict.get("job_title")
    if answers_dict.get("experience_years") and answers_dict["experience_years"] != "na":
        try:
            session.experience_years = int(answers_dict["experience_years"])
        except ValueError:
            pass
    session.prior_exposure = answers_dict.get("prior_exposure")
    session.learning_goals = answers_dict.get("learning_reason")
    session.preferred_modalities = answers_dict.get("preferred_modalities")
    if answers_dict.get("time_availability"):
        try:
            session.time_availability_hours = float(answers_dict["time_availability"])
        except ValueError:
            pass
    
    # Classify level using Gemini (no local threshold logic)
    level, explanation = classification_service.classify(
        request.answers,
        session.skill
    )
    
    # Store classification results
    session.assigned_level = level.value
    session.level_confidence = explanation.confidence
    session.classification_factors = explanation.factors
    
    await db.flush()
    
    return SubmitQuestionnaireResponse(
        session_id=request.session_id,
        assigned_level=level,
        explanation=explanation,
        next_step="diagnostic_quiz"
    )


@router.get("/classification-explanation")
async def get_classification_explanation():
    """
    Get explanation of how skill levels are determined by Gemini.
    
    This endpoint provides transparency about the classification process.
    
    Returns:
        Detailed explanation of Gemini-based classification methodology.
    """
    return {
        "methodology": "Gemini AI Classification using Dreyfus Model",
        "process": [
            "1. Questionnaire responses are formatted and sent to Gemini API",
            "2. Gemini analyzes all responses holistically",
            "3. Gemini classifies based on the Dreyfus Model of Skill Acquisition",
            "4. Classification is returned directly - no local threshold logic applied"
        ],
        "levels": {
            "beginner": {
                "dreyfus_stages": "Novice / Advanced Beginner",
                "description": "Little to no practical experience with the skill. Relies on explicit rules and step-by-step guidance. Needs support to recognize relevant features.",
                "gemini_indicators": [
                    "Low self-assessment scores",
                    "No prior professional exposure",
                    "Learning goals focused on fundamentals"
                ]
            },
            "intermediate": {
                "dreyfus_stages": "Competent",
                "description": "Meaningful experience with the skill (typically 1-3 years). Can plan and execute tasks independently. Applies rules flexibly based on context.",
                "gemini_indicators": [
                    "Moderate self-assessment scores",
                    "Completed projects or professional work",
                    "Can troubleshoot and problem-solve"
                ]
            },
            "advanced": {
                "dreyfus_stages": "Proficient / Expert",
                "description": "Extensive experience with the skill (typically 3+ years). Uses intuition and pattern recognition. Can teach and mentor others.",
                "gemini_indicators": [
                    "High self-assessment scores",
                    "Significant professional or teaching experience",
                    "Innovates and adapts to novel situations"
                ]
            }
        },
        "gemini_prompt_structure": {
            "input": "Formatted questionnaire responses including self-ratings, experience, prior exposure, and goals",
            "output": "JSON with level, confidence score (0-1), and reasoning factors",
            "model": "gemini-2.0-flash"
        },
        "transparency": {
            "can_challenge": True,
            "quiz_adjustment": "Diagnostic quiz scores may adjust the initial classification",
            "data_usage": "Responses are sent to Gemini API for classification only"
        },
        "note": "Classification is performed by Google's Gemini AI. Results include Gemini's reasoning for full transparency."
    }
