"""
YouTube Data API v3 client for fetching videos, details, and comments.

Features:
1. Search for videos
2. Fetch full video metadata (statistics, duration, etc.)
3. Fetch video comments for sentiment analysis
4. Extract video IDs from various URL formats

API Key should be set via YOUTUBE_API_KEY environment variable.
"""

import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import httpx

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class YouTubeVideo:
    """Represents a YouTube video with verified data."""
    video_id: str
    title: str
    channel_name: str
    description: str
    thumbnail_url: str
    url: str
    duration: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    published_at: Optional[str] = None
    platform: str = "YouTube"


@dataclass
class YouTubeComment:
    """Represents a YouTube comment."""
    text: str
    author: str
    like_count: int = 0
    published_at: Optional[str] = None


@dataclass 
class VideoAnalysis:
    """Full video analysis with metadata and sentiment."""
    video_id: str
    title: str
    channel_title: str
    view_count: int
    duration: str
    description: str
    link: str
    platform: str = "YouTube"
    published_at: Optional[str] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    sentiment: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class YouTubeClient:
    """
    Client for YouTube Data API v3.
    
    Provides methods for:
    - Searching videos
    - Fetching video details
    - Fetching video comments
    - Extracting video IDs from URLs
    """
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    # Patterns for extracting video IDs from URLs
    VIDEO_ID_PATTERNS = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Just the video ID itself
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'youtube_api_key', None)
        self._client = httpx.Client(timeout=15.0)
        
        if not self.api_key:
            logger.warning("YouTube API key not configured")
    
    def is_available(self) -> bool:
        """Check if the YouTube API is configured."""
        return bool(self.api_key)
    
    @staticmethod
    def extract_video_id(url_or_id: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.
        
        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID
        - https://youtube.com/watch?v=VIDEO_ID
        - URLs with extra parameters like &t= or &list=
        - Just the video ID itself
        
        Returns:
            Video ID string or None if extraction fails
        """
        if not url_or_id:
            return None
        
        url_or_id = url_or_id.strip()
        
        for pattern in YouTubeClient.VIDEO_ID_PATTERNS:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return None
    
    def search_videos(
        self,
        query: str,
        max_results: int = 3,
        video_duration: str = "any",
        order: str = "relevance",
        safe_search: str = "moderate"
    ) -> List[YouTubeVideo]:
        """Search YouTube for videos matching the query."""
        if not self.api_key:
            logger.warning("YouTube API not configured")
            return []
        
        try:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(max_results, 10),
                "order": order,
                "safeSearch": safe_search,
                "videoDuration": video_duration,
                "relevanceLanguage": "en",
                "key": self.api_key
            }
            
            response = self._client.get(f"{self.BASE_URL}/search", params=params)
            
            if response.status_code == 403:
                logger.error("YouTube API quota exceeded or invalid key")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            videos = []
            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                
                snippet = item.get("snippet", {})
                videos.append(YouTubeVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    channel_name=snippet.get("channelTitle", ""),
                    description=snippet.get("description", "")[:300],
                    thumbnail_url=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    published_at=snippet.get("publishedAt")
                ))
            
            logger.info(f"YouTube search returned {len(videos)} videos for: {query[:50]}")
            return videos
            
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            return []
    
    def search_educational_videos(
        self,
        skill: str,
        level: str,
        topic: Optional[str] = None,
        max_results: int = 3
    ) -> List[YouTubeVideo]:
        """Search for educational videos tailored to skill and level."""
        level_keywords = {
            "beginner": "tutorial for beginners complete course",
            "intermediate": "tutorial intermediate projects",
            "advanced": "advanced tutorial deep dive"
        }
        
        level_terms = level_keywords.get(level.lower(), level_keywords["beginner"])
        
        if topic:
            query = f"{skill} {topic} {level_terms}"
        else:
            query = f"{skill} {level_terms}"
        
        duration = "medium" if level == "beginner" else "any"
        
        return self.search_videos(
            query=query,
            max_results=max_results,
            video_duration=duration,
            order="relevance"
        )
    
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full video details including statistics.
        
        Returns dict with: snippet, statistics, contentDetails
        """
        if not self.api_key:
            return None
        
        try:
            params = {
                "part": "snippet,statistics,contentDetails",
                "id": video_id,
                "key": self.api_key
            }
            
            response = self._client.get(f"{self.BASE_URL}/videos", params=params)
            
            if response.status_code == 403:
                logger.error("YouTube API quota exceeded")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if not items:
                logger.warning(f"Video not found: {video_id}")
                return None
            
            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            
            return {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)) if stats.get("likeCount") else None,
                "comment_count": int(stats.get("commentCount", 0)) if stats.get("commentCount") else None,
                "duration": content.get("duration", ""),
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "platform": "YouTube"
            }
            
        except Exception as e:
            logger.error(f"Error fetching video details for {video_id}: {e}")
            return None
    
    def get_video_comments(
        self,
        video_id: str,
        max_results: int = 100
    ) -> Tuple[List[YouTubeComment], bool]:
        """
        Fetch comments for a video.
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum comments to fetch (up to 100 per request)
        
        Returns:
            Tuple of (list of comments, comments_available flag)
        """
        if not self.api_key:
            return [], False
        
        comments = []
        
        try:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(max_results, 100),
                "textFormat": "plainText",
                "order": "relevance",
                "key": self.api_key
            }
            
            response = self._client.get(f"{self.BASE_URL}/commentThreads", params=params)
            
            if response.status_code == 403:
                # Could be quota or comments disabled
                error_data = response.json()
                error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                
                if error_reason == "commentsDisabled":
                    logger.info(f"Comments disabled for video: {video_id}")
                    return [], False
                    
                logger.error(f"YouTube API error: {error_reason}")
                return [], False
            
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("items", []):
                snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                
                comment_text = snippet.get("textDisplay", "").strip()
                if comment_text:
                    comments.append(YouTubeComment(
                        text=comment_text,
                        author=snippet.get("authorDisplayName", ""),
                        like_count=int(snippet.get("likeCount", 0)),
                        published_at=snippet.get("publishedAt")
                    ))
            
            logger.info(f"Fetched {len(comments)} comments for video: {video_id}")
            return comments, True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return [], False
            logger.error(f"HTTP error fetching comments: {e}")
            return [], False
        except Exception as e:
            logger.error(f"Error fetching comments for {video_id}: {e}")
            return [], False
    
    def get_full_video_analysis(self, video_id: str) -> Optional[VideoAnalysis]:
        """
        Get complete video data for analysis.
        
        Combines video details - comments are fetched separately for sentiment.
        """
        details = self.get_video_details(video_id)
        
        if not details:
            return None
        
        return VideoAnalysis(
            video_id=details["video_id"],
            title=details["title"],
            channel_title=details["channel_title"],
            view_count=details["view_count"],
            duration=self._format_duration(details["duration"]),
            description=details["description"][:500],
            link=details["link"],
            platform=details["platform"],
            published_at=details.get("published_at"),
            like_count=details.get("like_count"),
            comment_count=details.get("comment_count")
        )
    
    def _format_duration(self, iso_duration: str) -> str:
        """Convert ISO 8601 duration to human readable format."""
        if not iso_duration:
            return "Unknown"
        
        # Parse PT#H#M#S format
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
    
    def verify_video_exists(self, video_id: str) -> bool:
        """Verify that a video exists and is accessible."""
        return self.get_video_details(video_id) is not None
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()


class MockYouTubeClient:
    """Mock YouTube client for testing without API key."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def is_available(self) -> bool:
        return True
    
    @staticmethod
    def extract_video_id(url_or_id: str) -> Optional[str]:
        return YouTubeClient.extract_video_id(url_or_id)
    
    def search_videos(self, query: str, max_results: int = 3, **kwargs) -> List[YouTubeVideo]:
        base_title = query.split()[0].title() if query else "Programming"
        
        mock_videos = [
            YouTubeVideo(
                video_id="dQw4w9WgXcQ",
                title=f"{base_title} Complete Tutorial for Beginners",
                channel_name="freeCodeCamp.org",
                description=f"Learn {base_title} from scratch.",
                thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                view_count=1000000,
                duration="4:32:10"
            )
        ]
        return mock_videos[:max_results]
    
    def search_educational_videos(self, skill: str, level: str, topic: Optional[str] = None, max_results: int = 3) -> List[YouTubeVideo]:
        return self.search_videos(f"{skill} {level}", max_results)
    
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        return {
            "video_id": video_id,
            "title": "Mock Video Title",
            "channel_title": "Mock Channel",
            "description": "Mock description",
            "view_count": 500000,
            "like_count": 10000,
            "comment_count": 500,
            "duration": "PT1H30M",
            "link": f"https://www.youtube.com/watch?v={video_id}",
            "platform": "YouTube"
        }
    
    def get_video_comments(self, video_id: str, max_results: int = 100) -> Tuple[List[YouTubeComment], bool]:
        mock_comments = [
            YouTubeComment(text="Great tutorial! Very helpful.", author="User1", like_count=50),
            YouTubeComment(text="This is exactly what I needed.", author="User2", like_count=30),
            YouTubeComment(text="Clear explanation, thanks!", author="User3", like_count=20),
        ]
        return mock_comments, True
    
    def get_full_video_analysis(self, video_id: str) -> Optional[VideoAnalysis]:
        return VideoAnalysis(
            video_id=video_id,
            title="Mock Video",
            channel_title="Mock Channel",
            view_count=500000,
            duration="1:30:00",
            description="Mock description",
            link=f"https://www.youtube.com/watch?v={video_id}",
            like_count=10000,
            comment_count=500
        )
    
    def verify_video_exists(self, video_id: str) -> bool:
        return True
    
    def close(self):
        pass


# Module-level client instance
_youtube_client: Optional[YouTubeClient] = None


def get_youtube_client() -> YouTubeClient:
    """Get or create the YouTube API client."""
    global _youtube_client
    
    if _youtube_client is None:
        api_key = getattr(settings, 'youtube_api_key', None)
        
        if api_key:
            _youtube_client = YouTubeClient(api_key)
            logger.info("YouTube API client initialized")
        else:
            _youtube_client = MockYouTubeClient()
            logger.warning("YouTube API key not found - using mock client")
    
    return _youtube_client


def set_youtube_client(client):
    """Set a custom YouTube client (for testing)."""
    global _youtube_client
    _youtube_client = client
