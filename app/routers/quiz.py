"""
Diagnostic quiz endpoints.
Generates and scores level-appropriate quizzes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from ..models.schemas import (
    GetQuizResponse, SubmitQuizRequest, SubmitQuizResponse,
    SkillLevel, QuizQuestion
)
from ..models.database import get_db, Session as DBSession, Quiz as DBQuiz
from ..services.quiz_generator import quiz_generator_service
from ..services.classification import classification_service

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz"])


@router.get("/{session_id}", response_model=GetQuizResponse)
async def get_diagnostic_quiz(
    session_id: str,
    num_questions: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a diagnostic quiz for the learner's assigned level.
    
    The quiz difficulty is tailored to the learner's level:
    - Beginner: Basic terminology and recognition questions
    - Intermediate: Scenario-based multiple choice requiring application
    - Advanced: Open-ended or multi-step problem solving
    
    Args:
        session_id: The learning session ID
        num_questions: Optional override for number of questions (5-10)
    
    Returns:
        GetQuizResponse with quiz questions
    
    Example:
        GET /api/v1/quiz/abc-123?num_questions=7
    """
    # Get session
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    if not session.assigned_level:
        raise HTTPException(
            status_code=400,
            detail="Complete the questionnaire first to get your skill level"
        )
    
    level = SkillLevel(session.assigned_level)
    
    # Check for existing incomplete quiz
    existing_quiz = await db.execute(
        select(DBQuiz).where(
            DBQuiz.session_id == session_id,
            DBQuiz.completed_at.is_(None)
        )
    )
    existing = existing_quiz.scalar_one_or_none()
    
    if existing:
        # Return existing quiz
        return GetQuizResponse(
            session_id=session_id,
            quiz_id=existing.id,
            skill=session.skill,
            target_level=level,
            questions=[QuizQuestion(**q) for q in existing.questions],
            total_points=existing.total_points
        )
    
    # Generate new quiz
    quiz_id, questions, total_points = quiz_generator_service.generate_quiz(
        session.skill,
        level,
        num_questions
    )
    
    # Store quiz
    db_quiz = DBQuiz(
        id=quiz_id,
        session_id=session_id,
        target_level=level.value,
        questions=[q.model_dump() for q in questions],
        total_points=total_points
    )
    
    db.add(db_quiz)
    await db.flush()
    
    return GetQuizResponse(
        session_id=session_id,
        quiz_id=quiz_id,
        skill=session.skill,
        target_level=level,
        questions=questions,
        total_points=total_points
    )


@router.post("/submit", response_model=SubmitQuizResponse)
async def submit_quiz(
    request: SubmitQuizRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit quiz answers and receive score with potential level adjustment.
    
    The quiz is scored and may adjust the learner's level:
    - High score (>85%) on current level may upgrade to next level
    - Low score (<40%) may suggest a lower level
    
    Args:
        request: Session ID, quiz ID, and answers
    
    Returns:
        SubmitQuizResponse with score, results, and any level changes
    
    Example:
        POST /api/v1/quiz/submit
        {
            "session_id": "abc-123",
            "quiz_id": "quiz-456",
            "answers": [
                {"question_id": "py_b1", "answer": "b"},
                {"question_id": "py_b2", "answer": "a"}
            ]
        }
    """
    # Get session
    session_result = await db.execute(
        select(DBSession).where(DBSession.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    # Get quiz
    quiz_result = await db.execute(
        select(DBQuiz).where(
            DBQuiz.id == request.quiz_id,
            DBQuiz.session_id == request.session_id
        )
    )
    quiz = quiz_result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if quiz.completed_at:
        raise HTTPException(status_code=400, detail="Quiz already completed")
    
    # Score the quiz
    score_percentage, points_earned, total_points, results = quiz_generator_service.score_quiz(
        session.skill,
        quiz.questions,
        request.answers
    )
    
    # Store answers and results
    quiz.answers = [a.model_dump() for a in request.answers]
    quiz.score = score_percentage
    quiz.points_earned = points_earned
    quiz.completed_at = datetime.utcnow()
    
    # Check for level adjustment
    current_level = SkillLevel(session.assigned_level)
    quiz_difficulty = SkillLevel(quiz.target_level)
    
    new_level, feedback = classification_service.adjust_level_after_quiz(
        current_level,
        score_percentage,
        quiz_difficulty
    )
    
    level_updated = False
    if new_level and new_level != current_level:
        session.assigned_level = new_level.value
        quiz.level_adjusted = True
        quiz.new_level = new_level.value
        level_updated = True
    
    await db.flush()
    
    # Calculate skill score (1-10) based on level and quiz performance
    # Level provides base range: beginner=1-3, intermediate=4-6, advanced=7-9
    # Quiz score determines position within that range, with perfect score potentially reaching 10
    final_level = new_level if level_updated else current_level
    
    if final_level == SkillLevel.BEGINNER:
        base_score = 1
        max_range = 3  # Can score 1-3, or 4 if perfect
    elif final_level == SkillLevel.INTERMEDIATE:
        base_score = 4
        max_range = 3  # Can score 4-6, or 7 if perfect
    else:  # ADVANCED
        base_score = 7
        max_range = 3  # Can score 7-9, or 10 if perfect
    
    # Calculate skill score: base + (percentage * range)
    # Add bonus for high performers (>90% gets +1)
    range_score = (score_percentage / 100) * max_range
    skill_score = int(base_score + range_score)
    
    # Bonus point for exceptional performance
    if score_percentage >= 90 and skill_score < 10:
        skill_score += 1
    
    # Ensure bounds
    skill_score = max(1, min(10, skill_score))
    
    return SubmitQuizResponse(
        session_id=request.session_id,
        quiz_id=request.quiz_id,
        score=score_percentage,
        score_percentage=score_percentage,
        skill_score=skill_score,
        points_earned=points_earned,
        total_points=total_points,
        results=results,
        level_updated=level_updated,
        new_level=new_level if level_updated else None,
        feedback=feedback
    )


@router.get("/{session_id}/history")
async def get_quiz_history(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get quiz history for a session.
    
    Returns:
        List of completed quizzes with scores.
    """
    # Verify session exists
    session_result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    # Get quizzes
    quiz_result = await db.execute(
        select(DBQuiz).where(DBQuiz.session_id == session_id)
    )
    quizzes = quiz_result.scalars().all()
    
    return {
        "session_id": session_id,
        "quizzes": [
            {
                "quiz_id": q.id,
                "target_level": q.target_level,
                "score": q.score,
                "points_earned": q.points_earned,
                "total_points": q.total_points,
                "completed": q.completed_at is not None,
                "completed_at": q.completed_at.isoformat() if q.completed_at else None,
                "level_adjusted": q.level_adjusted,
                "new_level": q.new_level
            }
            for q in quizzes
        ],
        "total_quizzes": len(quizzes)
    }
