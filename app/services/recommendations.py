"""
Course and resource recommendation service.
Uses Gemini API to recommend courses from YouTube, Coursera, and Udemy.
"""

import json
import os
import re
from typing import Dict, Any, List, Optional
from ..models.schemas import (
    SkillLevel, Platform, LearningModality, ResourceRecommendation, ResourceFilter
)
from ..config import RESOURCES_FILE
from .gemini_client import get_client


class RecommendationService:
    """
    Service for recommending learning resources via Gemini API.
    
    Gemini is prompted to recommend 2-3 courses from:
    - YouTube: Free video tutorials with timestamp support
    - Coursera: University courses with free previews
    - Udemy: Marketplace courses (185,000+ in 75+ languages)
    
    The service formats Gemini's response into structured recommendations.
    """
    
    def __init__(self):
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_recommendations(
        self,
        skill: str,
        level: SkillLevel,
        filter_options: Optional[ResourceFilter] = None,
        preferred_modalities: Optional[List[LearningModality]] = None,
        time_availability_hours: Optional[float] = None,
        interests: Optional[str] = None,
        limit: int = 3
    ) -> List[ResourceRecommendation]:
        """
        Get personalized resource recommendations from Gemini.
        
        Assembles a prompt to Gemini asking for 2-3 course recommendations
        from YouTube, Coursera, or Udemy only.
        
        Args:
            skill: The skill to find resources for
            level: Learner's skill level
            filter_options: Optional filters (platforms, free_only, etc.)
            preferred_modalities: Preferred learning methods
            time_availability_hours: Weekly time budget
            interests: Specific interests or topics
            limit: Maximum number of recommendations (default 3)
        
        Returns:
            List of ResourceRecommendation from Gemini
        """
        # Convert modalities to strings for prompt
        modalities_str = []
        if preferred_modalities:
            modalities_str = [m.value for m in preferred_modalities]
        else:
            modalities_str = ["video"]
        
        # Get Gemini client
        client = get_client()
        
        try:
            # Ask Gemini for recommendations
            gemini_recommendations = client.get_course_recommendations(
                skill=skill,
                level=level.value,
                preferred_modalities=modalities_str,
                interests=interests,
                num_recommendations=limit
            )
            
            # Convert to ResourceRecommendation objects
            recommendations = []
            for rec_data in gemini_recommendations[:limit]:
                rec = self._parse_gemini_recommendation(rec_data)
                if rec:
                    # Apply filters if provided
                    if filter_options:
                        if filter_options.platforms:
                            if rec.platform not in filter_options.platforms:
                                continue
                        if filter_options.free_only and not rec.is_free:
                            continue
                        if filter_options.max_duration_hours:
                            if rec.duration_hours and rec.duration_hours > filter_options.max_duration_hours:
                                continue
                    
                    recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            print(f"Warning: Gemini recommendation failed: {e}")
            # Return empty list on error - no fallback to static data
            return []
    
    def _ensure_safe_url(self, url: str, platform: str, title: str) -> str:
        """
        Ensure URL is a safe search URL that will always work.
        Convert specific video/course URLs to search URLs to avoid broken links.
        """
        import urllib.parse
        
        # Extract search terms from title
        search_terms = re.sub(r'[^\w\s]', '', title).strip()
        search_encoded = urllib.parse.quote_plus(search_terms)
        
        if platform == "youtube":
            # If it's already a search URL, keep it
            if "/results?search_query=" in url:
                return url
            # Convert any other YouTube URL to a search URL
            return f"https://www.youtube.com/results?search_query={search_encoded}"
        
        elif platform == "coursera":
            # If it's already a search URL, keep it
            if "/search?" in url:
                return url
            # Convert to search URL
            return f"https://www.coursera.org/search?query={search_encoded}"
        
        elif platform == "udemy":
            # If it's already a search URL, keep it
            if "/courses/search/?" in url or "/courses/search?" in url:
                return url
            # Convert to search URL
            return f"https://www.udemy.com/courses/search/?q={search_encoded}&sort=relevance&ratings=4.0"
        
        return url
    
    def _parse_gemini_recommendation(self, rec_data: Dict[str, Any]) -> Optional[ResourceRecommendation]:
        """
        Parse a single recommendation from Gemini's response.
        
        Args:
            rec_data: Dictionary from Gemini response
        
        Returns:
            ResourceRecommendation or None if parsing fails
        """
        try:
            platform_str = rec_data.get("platform", "").lower()
            if platform_str not in ["youtube", "coursera", "udemy"]:
                return None
            
            platform = Platform(platform_str)
            title = rec_data.get("title", "Unknown Course")
            url = rec_data.get("url", "")
            
            # ALWAYS convert to safe search URL to avoid broken links
            url = self._ensure_safe_url(url, platform_str, title)
            
            # No embed URLs - just use search URLs
            embed_url = None
            
            # Parse difficulty
            diff_str = rec_data.get("difficulty", "intermediate").lower()
            try:
                difficulty = SkillLevel(diff_str)
            except ValueError:
                difficulty = SkillLevel.INTERMEDIATE
            
            return ResourceRecommendation(
                resource_id=f"{platform_str}_{hash(url) % 10000}",
                title=title,
                platform=platform,
                url=url,
                embed_url=embed_url,
                topic_coverage=[],  # Gemini doesn't return this
                difficulty=difficulty,
                duration_hours=rec_data.get("duration_hours"),
                rating=rec_data.get("rating"),
                is_free=rec_data.get("is_free", False),
                price=rec_data.get("price"),
                affiliate_link=None,
                snippet_start=None,
                snippet_end=None,
                relevance_score=0.9  # High relevance since Gemini curated it
            )
            
        except Exception as e:
            print(f"Warning: Could not parse recommendation: {e}")
            return None
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If URL doesn't match standard patterns, try to extract any 11-char ID
        if "youtube" in url.lower() or "youtu.be" in url.lower():
            # Look for 11-character alphanumeric segments
            match = re.search(r'[a-zA-Z0-9_-]{11}', url)
            if match:
                return match.group(0)
        
        return None


recommendation_service = RecommendationService()
