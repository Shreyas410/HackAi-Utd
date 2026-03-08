"""
Scenario-based practice endpoints.
Provides interactive scenarios with branching logic.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from ..models.schemas import (
    ScenarioResponse, ScenarioActionRequest, ScenarioFeedback, SkillLevel
)
from ..models.database import get_db, Session as DBSession, ScenarioAttempt
from ..services.scenario import scenario_service

router = APIRouter(prefix="/api/v1/practice", tags=["Practice"])


@router.get("/{session_id}/scenarios")
async def list_available_scenarios(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    List available practice scenarios for the learner's level.
    
    Args:
        session_id: The learning session ID
    
    Returns:
        List of available scenarios with metadata.
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
    
    level = SkillLevel(session.assigned_level) if session.assigned_level else None
    scenarios = scenario_service.get_available_scenarios(session.skill, level)
    
    return {
        "session_id": session_id,
        "skill": session.skill,
        "learner_level": session.assigned_level,
        "scenarios": scenarios,
        "total": len(scenarios)
    }


@router.post("/{session_id}/start", response_model=ScenarioResponse)
async def start_scenario(
    session_id: str,
    scenario_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new scenario-based practice session.
    
    Each scenario presents realistic situations with decision points.
    The learner's choices lead to different consequences and feedback.
    
    Args:
        session_id: The learning session ID
        scenario_id: Optional specific scenario to start
    
    Returns:
        ScenarioResponse with initial situation and actions
    
    Example:
        POST /api/v1/practice/abc-123/start?scenario_id=py_scenario_1
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
            detail="Complete the questionnaire first to determine your level"
        )
    
    level = SkillLevel(session.assigned_level)
    
    # Start scenario
    scenario_instance_id, title, skill, outcomes, first_node = scenario_service.start_scenario(
        session_id,
        session.skill,
        level,
        scenario_id
    )
    
    # Record attempt
    attempt = ScenarioAttempt(
        session_id=session_id,
        scenario_id=scenario_instance_id,
        current_node_id=first_node.node_id
    )
    db.add(attempt)
    await db.flush()
    
    return ScenarioResponse(
        session_id=session_id,
        scenario_id=scenario_instance_id,
        title=title,
        skill=skill,
        difficulty=level,
        learning_outcomes=outcomes,
        current_node=first_node
    )


@router.post("/action", response_model=ScenarioFeedback)
async def take_scenario_action(
    request: ScenarioActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Take an action in an active scenario.
    
    Each action leads to consequences and feedback. The scenario
    may continue with new decision points or complete.
    
    Args:
        request: Session ID, scenario ID, current node, and chosen action
    
    Returns:
        ScenarioFeedback with consequences, feedback, and next node (if any)
    
    Example:
        POST /api/v1/practice/action
        {
            "session_id": "abc-123",
            "scenario_id": "py_scenario_1_abc12345",
            "node_id": "start",
            "action_id": "a2"
        }
    """
    # Verify session
    session_result = await db.execute(
        select(DBSession).where(DBSession.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    # Process action
    feedback = scenario_service.take_action(
        request.session_id,
        request.scenario_id,
        request.node_id,
        request.action_id
    )
    
    # Update attempt record
    attempt_result = await db.execute(
        select(ScenarioAttempt).where(
            ScenarioAttempt.session_id == request.session_id,
            ScenarioAttempt.scenario_id == request.scenario_id
        )
    )
    attempt = attempt_result.scalar_one_or_none()
    
    if attempt:
        actions_taken = attempt.actions_taken or []
        actions_taken.append({
            "node_id": request.node_id,
            "action_id": request.action_id,
            "score_delta": feedback.score_delta
        })
        attempt.actions_taken = actions_taken
        attempt.score = (attempt.score or 0) + feedback.score_delta
        
        if feedback.next_node:
            attempt.current_node_id = feedback.next_node.node_id
        
        if feedback.scenario_complete:
            attempt.completed_at = datetime.utcnow()
    
    await db.flush()
    
    return feedback


@router.get("/{session_id}/status")
async def get_scenario_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current status of an active scenario.
    
    Returns:
        Current scenario state including node, score, and actions taken.
    """
    # Verify session
    session_result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    state = scenario_service.get_scenario_state(session_id)
    
    if not state:
        return {
            "session_id": session_id,
            "active_scenario": False,
            "message": "No active scenario. Start one with POST /practice/{session_id}/start"
        }
    
    return {
        "session_id": session_id,
        "active_scenario": True,
        **state
    }


@router.get("/{session_id}/history")
async def get_practice_history(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get practice history for a session.
    
    Returns:
        List of completed scenarios with scores.
    """
    # Verify session
    session_result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.data_deleted:
        raise HTTPException(status_code=410, detail="Session data has been deleted")
    
    # Get attempts
    attempts_result = await db.execute(
        select(ScenarioAttempt).where(ScenarioAttempt.session_id == session_id)
    )
    attempts = attempts_result.scalars().all()
    
    return {
        "session_id": session_id,
        "attempts": [
            {
                "scenario_id": a.scenario_id,
                "score": a.score,
                "actions_count": len(a.actions_taken) if a.actions_taken else 0,
                "started_at": a.started_at.isoformat() if a.started_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "completed": a.completed_at is not None
            }
            for a in attempts
        ],
        "total_attempts": len(attempts),
        "completed_count": sum(1 for a in attempts if a.completed_at)
    }
