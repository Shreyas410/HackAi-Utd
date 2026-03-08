"""
Video Analysis API Router.

Provides endpoints for:
1. Analyzing a single YouTube video (sentiment, engagement)
2. Comparing two YouTube videos
3. Analyzing recommended videos from the learning system
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.youtube_client import get_youtube_client, YouTubeClient
from ..services.sentiment_analyzer import (
    get_sentiment_analyzer, get_video_comparer,
    SentimentResult, VideoComparison
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/video-analysis", tags=["Video Analysis"])


# ==================== Request/Response Models ====================

class VideoAnalysisResponse(BaseModel):
    """Response for single video analysis."""
    videoId: str
    title: str
    channelTitle: str
    viewCount: int
    duration: str
    description: str
    link: str
    platform: str = "YouTube"
    publishedAt: Optional[str] = None
    likeCount: Optional[int] = None
    commentCount: Optional[int] = None
    sentiment: dict = Field(default_factory=dict)


class SentimentData(BaseModel):
    """Sentiment analysis data."""
    score: float = Field(ge=0, le=5)
    summary: str
    confidence: float = Field(ge=0, le=1)
    positive_count: int
    negative_count: int
    neutral_count: int
    total_comments: int
    note: Optional[str] = None


class ComparisonResult(BaseModel):
    """Result of comparing two videos."""
    better_video: str  # "recommended_video", "comparison_video", or "inconclusive"
    reason: str
    score_difference: float
    confidence_note: str


class VideoComparisonResponse(BaseModel):
    """Response for video comparison."""
    recommended_video: VideoAnalysisResponse
    comparison_video: VideoAnalysisResponse
    comparison_result: ComparisonResult


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str


class CompareRequest(BaseModel):
    """Request to compare a video against the recommended one."""
    comparison_url: str = Field(..., description="YouTube URL to compare")
    recommended_video_id: Optional[str] = Field(None, description="Video ID of the recommended video (if already analyzed)")


# ==================== Helper Functions ====================

def analyze_video(video_id: str) -> dict:
    """
    Analyze a single video and return full analysis data.
    """
    youtube = get_youtube_client()
    analyzer = get_sentiment_analyzer()
    
    # Fetch video details
    details = youtube.get_video_details(video_id)
    if not details:
        return {"error": "VIDEO_NOT_FOUND", "message": f"Could not find video: {video_id}"}
    
    # Fetch comments
    comments, comments_available = youtube.get_video_comments(video_id, max_results=100)
    
    # Analyze sentiment
    sentiment = analyzer.analyze_comments(comments, comments_available)
    
    return {
        "videoId": details["video_id"],
        "title": details["title"],
        "channelTitle": details["channel_title"],
        "viewCount": details["view_count"],
        "duration": _format_duration(details.get("duration", "")),
        "description": details["description"][:500] if details.get("description") else "",
        "link": details["link"],
        "platform": "YouTube",
        "publishedAt": details.get("published_at"),
        "likeCount": details.get("like_count"),
        "commentCount": details.get("comment_count"),
        "sentiment": {
            "score": sentiment.score,
            "summary": sentiment.summary,
            "confidence": sentiment.confidence,
            "positive_count": sentiment.positive_count,
            "negative_count": sentiment.negative_count,
            "neutral_count": sentiment.neutral_count,
            "total_comments": sentiment.total_comments,
            "note": sentiment.note
        }
    }


def _format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration to human readable format."""
    if not iso_duration:
        return "Unknown"
    
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return iso_duration
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


# ==================== API Endpoints ====================

@router.get(
    "/analyze",
    response_model=VideoAnalysisResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def analyze_single_video(
    video_url: Optional[str] = Query(None, description="YouTube video URL"),
    video_id: Optional[str] = Query(None, description="YouTube video ID")
):
    """
    Analyze a single YouTube video.
    
    Fetches video metadata, comments, and performs sentiment analysis.
    Provide either video_url or video_id.
    """
    # Extract video ID
    if video_url:
        extracted_id = YouTubeClient.extract_video_id(video_url)
        if not extracted_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_YOUTUBE_LINK",
                    "message": "Could not extract a valid YouTube video ID from the provided link."
                }
            )
        video_id = extracted_id
    
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "MISSING_INPUT",
                "message": "Please provide either video_url or video_id"
            }
        )
    
    # Check API availability
    youtube = get_youtube_client()
    if not youtube.is_available():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "YOUTUBE_API_ERROR",
                "message": "YouTube API is not configured. Please set YOUTUBE_API_KEY."
            }
        )
    
    # Analyze the video
    result = analyze_video(video_id)
    
    if "error" in result:
        status_code = 404 if result["error"] == "VIDEO_NOT_FOUND" else 500
        raise HTTPException(status_code=status_code, detail=result)
    
    return result


@router.post(
    "/compare",
    response_model=VideoComparisonResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def compare_videos(request: CompareRequest):
    """
    Compare two YouTube videos.
    
    Analyzes both videos and returns a side-by-side comparison
    with a recommendation based on sentiment and engagement.
    """
    youtube = get_youtube_client()
    comparer = get_video_comparer()
    
    if not youtube.is_available():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "YOUTUBE_API_ERROR", 
                "message": "YouTube API is not configured."
            }
        )
    
    # Extract comparison video ID
    comparison_id = YouTubeClient.extract_video_id(request.comparison_url)
    if not comparison_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_YOUTUBE_LINK",
                "message": "Could not extract a valid YouTube video ID from the comparison URL."
            }
        )
    
    # Get recommended video ID (either from request or we need it)
    if not request.recommended_video_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "MISSING_INPUT",
                "message": "Please provide recommended_video_id to compare against."
            }
        )
    
    recommended_id = YouTubeClient.extract_video_id(request.recommended_video_id)
    if not recommended_id:
        recommended_id = request.recommended_video_id  # Assume it's already just the ID
    
    # Analyze both videos
    recommended_analysis = analyze_video(recommended_id)
    comparison_analysis = analyze_video(comparison_id)
    
    # Check for errors
    if "error" in recommended_analysis:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "VIDEO_NOT_FOUND",
                "message": f"Could not find recommended video: {recommended_id}"
            }
        )
    
    if "error" in comparison_analysis:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "VIDEO_NOT_FOUND", 
                "message": f"Could not find comparison video: {comparison_id}"
            }
        )
    
    # Compare the videos
    comparison = comparer.compare(recommended_analysis, comparison_analysis)
    
    return {
        "recommended_video": comparison.recommended_video,
        "comparison_video": comparison.comparison_video,
        "comparison_result": comparison.comparison_result
    }


@router.get(
    "/analyze-by-query",
    response_model=VideoAnalysisResponse,
    responses={404: {"model": ErrorResponse}}
)
async def analyze_by_search_query(
    query: str = Query(..., description="Search query for finding a video"),
    skill: Optional[str] = Query(None, description="Skill context for better search"),
    level: Optional[str] = Query(None, description="Skill level (beginner/intermediate/advanced)")
):
    """
    Search for a video and analyze it.
    
    Finds the best matching video for the query and performs full analysis.
    """
    youtube = get_youtube_client()
    
    if not youtube.is_available():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "YOUTUBE_API_ERROR",
                "message": "YouTube API is not configured."
            }
        )
    
    # Build search query
    search_query = query
    if skill:
        search_query = f"{skill} {query}"
    if level:
        level_terms = {
            "beginner": "tutorial for beginners",
            "intermediate": "intermediate tutorial",
            "advanced": "advanced tutorial"
        }
        search_query += f" {level_terms.get(level.lower(), '')}"
    
    # Search for videos
    videos = youtube.search_videos(search_query, max_results=1)
    
    if not videos:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "VIDEO_NOT_FOUND",
                "message": f"No videos found for query: {query}"
            }
        )
    
    # Analyze the top result
    result = analyze_video(videos[0].video_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result)
    
    return result


@router.get("/health")
async def health_check():
    """Check if video analysis service is available."""
    youtube = get_youtube_client()
    return {
        "status": "ok",
        "youtube_api_available": youtube.is_available()
    }
