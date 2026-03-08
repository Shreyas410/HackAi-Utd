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
    RecommendationMeta, SkillLevel, Platform, LearningModality
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
    
    # Get recommendations using hybrid pipeline
    recommendations, meta = recommendation_service.get_recommendations(
        skill=session.skill,
        level=level,
        filter_options=filter_options,
        preferred_modalities=preferred_modalities,
        time_availability_hours=session.time_availability_hours,
        limit=limit
    )
    
    # Build metadata response with verified-link-first pipeline info
    recommendation_meta = RecommendationMeta(
        skill=meta.get("skill", session.skill),
        level=meta.get("level", level.value),
        youtube_api_used=meta.get("youtube_api_used", False),
        curated_used=meta.get("curated_used", False),
        gemini_used=meta.get("gemini_used", False),
        resolved_curated_used=meta.get("resolved_curated_used", False),
        generic_curated_used=meta.get("generic_curated_used", False),
        search_fallback_used=meta.get("search_fallback_used", False),
        direct_count=meta.get("direct_count", 0),
        search_count=meta.get("search_count", 0),
        total_candidates=meta.get("total_candidates", 0),
        total_returned=meta.get("total_returned", len(recommendations))
    )
    
    return ResourceRecommendationResponse(
        session_id=session_id,
        learner_level=level,
        recommendations=recommendations,
        total_available=len(recommendations),
        meta=recommendation_meta
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
    requiring a learning session. Uses the hybrid pipeline
    to generate recommendations for the specified skill.
    
    Args:
        skill: Skill to get resources for (required for meaningful results)
        platform: Optional platform filter (youtube, coursera, udemy)
        difficulty: Optional difficulty filter (defaults to beginner)
        free_only: Only return free resources
        limit: Maximum results to return
    
    Returns:
        List of resources matching the filters
    """
    # Default skill if not provided
    target_skill = skill or "programming"
    target_level = difficulty or SkillLevel.BEGINNER
    
    # Build filter
    filter_options = ResourceFilter(
        session_id="catalog",
        platforms=[platform] if platform else None,
        free_only=free_only
    )
    
    # Get recommendations using hybrid pipeline
    recommendations, meta = recommendation_service.get_recommendations(
        skill=target_skill,
        level=target_level,
        filter_options=filter_options,
        limit=limit
    )
    
    return {
        "resources": [r.model_dump() for r in recommendations],
        "total": meta.get("total_candidates", len(recommendations)),
        "returned": len(recommendations),
        "filters_applied": {
            "skill": target_skill,
            "platform": platform.value if platform else None,
            "difficulty": target_level.value if target_level else None,
            "free_only": free_only
        },
        "meta": meta
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
