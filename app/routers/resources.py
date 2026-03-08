"""
Course and resource recommendation endpoints.
Matches learners with resources from YouTube, Coursera, and Udemy.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from ..models.schemas import (
    ResourceRecommendationResponse, ResourceFilter, ResourceRecommendation,
    SkillLevel, Platform, LearningModality
)
from ..models.database import get_db, Session as DBSession
from ..services.recommendations import recommendation_service

router = APIRouter(prefix="/api/v1/resources", tags=["Resources"])


@router.get("/{session_id}/recommendations", response_model=ResourceRecommendationResponse)
async def get_resource_recommendations(
    session_id: str,
    limit: int = Query(default=5, ge=1, le=10, description="Max recommendations to return"),
    platforms: Optional[List[Platform]] = Query(default=None, description="Filter by platforms"),
    free_only: bool = Query(default=False, description="Only return free resources"),
    max_duration_hours: Optional[float] = Query(default=None, description="Max course duration"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized resource recommendations for a learner.
    
    Recommendations are filtered and ranked based on:
    - Learner's skill level
    - Preferred learning modalities
    - Time availability
    - Platform preferences
    
    Resources are sourced from:
    - YouTube: Free video tutorials with embed support and time-based snippets
    - Coursera: University courses with free audit and paid certificates
    - Udemy: Marketplace courses (often on sale)
    
    Args:
        session_id: The learning session ID
        limit: Maximum number of recommendations (1-10)
        platforms: Filter by specific platforms
        free_only: Only return free resources
        max_duration_hours: Filter by maximum duration
    
    Returns:
        ResourceRecommendationResponse with ranked recommendations
    
    Example:
        GET /api/v1/resources/abc-123?limit=5&free_only=true&platforms=youtube&platforms=coursera
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
            detail="Complete the questionnaire first to get personalized recommendations"
        )
    
    level = SkillLevel(session.assigned_level)
    
    # Parse preferred modalities from session
    preferred_modalities = None
    if session.preferred_modalities:
        if isinstance(session.preferred_modalities, list):
            preferred_modalities = [
                LearningModality(m) for m in session.preferred_modalities
                if m in [e.value for e in LearningModality]
            ]
    
    # Build filter
    filter_options = ResourceFilter(
        session_id=session_id,
        platforms=platforms,
        max_duration_hours=max_duration_hours,
        free_only=free_only,
        modalities=preferred_modalities
    )
    
    # Get recommendations
    recommendations = recommendation_service.get_recommendations(
        skill=session.skill,
        level=level,
        filter_options=filter_options,
        preferred_modalities=preferred_modalities,
        time_availability_hours=session.time_availability_hours,
        limit=limit
    )
    
    return ResourceRecommendationResponse(
        session_id=session_id,
        learner_level=level,
        recommendations=recommendations,
        total_available=len(recommendations)
    )


@router.get("/catalog/all")
async def browse_all_resources(
    skill: Optional[str] = Query(default=None, description="Filter by skill"),
    platform: Optional[Platform] = Query(default=None, description="Filter by platform"),
    difficulty: Optional[SkillLevel] = Query(default=None, description="Filter by difficulty"),
    free_only: bool = Query(default=False, description="Only free resources"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results")
):
    """
    Browse the resource catalog without a session.
    
    This endpoint allows exploring available resources without
    requiring a learning session.
    
    Args:
        skill: Optional skill filter
        platform: Optional platform filter (youtube, coursera, udemy)
        difficulty: Optional difficulty filter
        free_only: Only return free resources
        limit: Maximum results to return
    
    Returns:
        List of resources matching the filters
    """
    # Get all resources with basic filtering
    all_resources = recommendation_service._resources
    
    filtered = all_resources
    
    if skill:
        skill_lower = skill.lower()
        filtered = [
            r for r in filtered
            if any(skill_lower in s.lower() for s in r.get("skills", []))
        ]
    
    if platform:
        filtered = [r for r in filtered if r.get("platform") == platform.value]
    
    if difficulty:
        filtered = [r for r in filtered if r.get("difficulty") == difficulty.value]
    
    if free_only:
        filtered = [r for r in filtered if r.get("is_free", False)]
    
    # Convert to recommendations
    results = []
    for r in filtered[:limit]:
        rec = recommendation_service._to_recommendation(r, 0.5)
        results.append(rec)
    
    return {
        "resources": [r.model_dump() for r in results],
        "total": len(filtered),
        "returned": len(results),
        "filters_applied": {
            "skill": skill,
            "platform": platform.value if platform else None,
            "difficulty": difficulty.value if difficulty else None,
            "free_only": free_only
        }
    }


@router.get("/platforms/info")
async def get_platform_info():
    """
    Get information about supported resource platforms.
    
    Returns:
        Details about YouTube, Coursera, and Udemy.
    """
    return {
        "platforms": {
            "youtube": {
                "name": "YouTube",
                "description": "Free video tutorials and educational content",
                "pricing": "Free",
                "features": [
                    "Time-based snippets with start/end parameters",
                    "Embed support for integration",
                    "Vast range of educational content",
                    "Multiple languages and styles"
                ],
                "embed_format": "https://www.youtube.com/embed/{video_id}?start={seconds}&end={seconds}"
            },
            "coursera": {
                "name": "Coursera",
                "description": "University and company courses with certificates",
                "pricing": "Free audit / $49+ per month for certificates",
                "features": [
                    "Thousands of courses from top universities",
                    "Professional certificates and degrees",
                    "Free previews and audit options",
                    "Structured learning paths"
                ],
                "note": "Free audit allows access to course materials; certificates require payment"
            },
            "udemy": {
                "name": "Udemy",
                "description": "Marketplace with 185,000+ courses in 75+ languages",
                "pricing": "Varies ($12.99 - $199.99, frequent sales)",
                "features": [
                    "Largest course marketplace",
                    "Lifetime access to purchased courses",
                    "Frequent sales (courses often $12.99-$19.99)",
                    "75+ languages supported",
                    "Tens of millions of learners"
                ],
                "note": "Watch for sales - courses are heavily discounted regularly"
            }
        },
        "note": "Resource filtering is currently limited to these three platforms. The system is modular and can be extended to support additional providers."
    }
