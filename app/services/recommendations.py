"""
Hybrid direct-link-first recommendation service with YouTube API integration.

Pipeline Priority:
1. YouTube API verified videos (100% working links)
2. Curated direct course links (manually verified)
3. Gemini suggestions resolved to curated links
4. Generic curated direct links
5. Search URL fallback (last resort)

The goal: Open real course pages, not search results.
"""

import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..models.schemas import (
    SkillLevel, Platform, LearningModality, ResourceRecommendation, ResourceFilter
)
from ..data.curated_resources import (
    get_curated_resources, get_generic_direct_resources,
    get_all_curated_for_matching, get_level_modifiers, normalize_skill_name
)
from .gemini_client import get_client
from .youtube_client import get_youtube_client, YouTubeVideo

logger = logging.getLogger(__name__)


PLATFORM_DOMAINS = {
    "youtube": ["youtube.com", "youtu.be"]
}

SUPPORTED_PLATFORMS = {"youtube"}


@dataclass
class RecommendationCandidate:
    """Internal representation of a recommendation candidate."""
    title: str
    platform: str
    url: str
    url_type: str  # "direct" or "search"
    description: str = ""
    reason: str = ""
    difficulty: str = "intermediate"
    source: str = "unknown"  # curated, gemini, resolved_curated, generic_curated, fallback_search
    score: float = 0.0
    is_free: bool = True
    duration_hours: Optional[float] = None
    rating: Optional[float] = None
    query: str = ""  # Kept for search fallback
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "platform": self.platform,
            "url": self.url,
            "url_type": self.url_type,
            "description": self.description,
            "why_recommended": self.reason,
            "difficulty": self.difficulty,
            "source": self.source,
            "score": self.score,
            "is_free": self.is_free,
            "duration_hours": self.duration_hours,
            "rating": self.rating
        }


class RecommendationService:
    """
    Direct-link-first recommendation service.
    
    Prioritizes actual course URLs over search results.
    """
    
    def __init__(self):
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
    
    # ==================== URL Validation ====================
    
    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name."""
        if not platform:
            return ""
        platform = platform.lower().strip()
        return platform if platform in SUPPORTED_PLATFORMS else ""
    
    def _is_valid_platform_url(self, url: str, platform: str) -> bool:
        """Check if URL belongs to the platform."""
        if not url or not platform:
            return False
        
        url_lower = url.lower()
        domains = PLATFORM_DOMAINS.get(platform, [])
        
        if not url_lower.startswith("http"):
            return False
        
        return any(domain in url_lower for domain in domains)
    
    def _is_direct_course_url(self, url: str, platform: str) -> bool:
        """
        Check if URL is a direct course/video page, not a search/category page.
        
        Direct URLs:
        - YouTube: /watch?v=, /playlist?list=, youtu.be/
        - Coursera: /learn/, /specializations/, /professional-certificates/
        - Udemy: /course/
        """
        if not url or not platform:
            return False
        
        url_lower = url.lower()
        
        # Reject search/category URLs
        search_patterns = [
            r'/results\?',
            r'/search\?',
            r'/search/',
            r'/courses/search',
            r'/browse/',
            r'/categories/',
        ]
        for pattern in search_patterns:
            if re.search(pattern, url_lower):
                return False
        
        # Reject homepage URLs
        homepage_patterns = [
            r'^https?://(www\.)?youtube\.com/?$',
            r'^https?://(www\.)?coursera\.org/?$',
            r'^https?://(www\.)?udemy\.com/?$',
        ]
        for pattern in homepage_patterns:
            if re.match(pattern, url_lower):
                return False
        
        # Check for direct course patterns
        if platform == "youtube":
            # Direct video or playlist
            direct_patterns = [
                r'/watch\?v=[\w-]{11}',
                r'youtu\.be/[\w-]{11}',
                r'/playlist\?list=',
                r'/embed/[\w-]{11}',
            ]
            return any(re.search(p, url_lower) for p in direct_patterns)
        
        elif platform == "coursera":
            # Direct course, specialization, or certificate page
            direct_patterns = [
                r'/learn/[\w-]+',
                r'/specializations/[\w-]+',
                r'/professional-certificates/[\w-]+',
                r'/degrees/[\w-]+',
            ]
            return any(re.search(p, url_lower) for p in direct_patterns)
        
        elif platform == "udemy":
            # Direct course page
            return '/course/' in url_lower and '/courses/search' not in url_lower
        
        return False
    
    def _is_search_url(self, url: str, platform: str) -> bool:
        """Check if URL is a search/results page."""
        if not url:
            return False
        
        if platform == "youtube":
            return "/results?search_query=" in url
        elif platform == "coursera":
            return "/search?" in url
        elif platform == "udemy":
            return "/courses/search/" in url or "/courses/search?" in url
        
        return False
    
    # ==================== Search URL Building (Fallback) ====================
    
    def _build_search_query(
        self,
        title: Optional[str],
        query: Optional[str],
        skill: str,
        level: str,
        platform: str
    ) -> str:
        """Build search query from available data."""
        if query and query.strip():
            return query.strip()
        
        parts = []
        if title:
            clean_title = re.sub(r'\b(youtube|coursera|udemy|tutorial|course)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            if clean_title:
                parts.append(clean_title)
        
        if skill and skill.lower() not in ' '.join(parts).lower():
            parts.insert(0, skill)
        
        level_mods = get_level_modifiers(level)
        if not any(mod in ' '.join(parts).lower() for mod in level_mods[:2]):
            parts.append(level_mods[0])
        
        return ' '.join(parts)
    
    def _build_youtube_search_url(self, query: str) -> str:
        """Build YouTube search URL (fallback only)."""
        encoded = urllib.parse.quote_plus(query)
        return f"https://www.youtube.com/results?search_query={encoded}"
    
    def _build_coursera_search_url(self, query: str, level: Optional[str] = None) -> str:
        """Build Coursera search URL (fallback only)."""
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.coursera.org/search?query={encoded}"
        if level:
            level_map = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
            if level.lower() in level_map:
                url += f"&productDifficultyLevel={level_map[level.lower()]}"
        return url
    
    def _build_udemy_search_url(self, query: str, level: Optional[str] = None) -> str:
        """Build Udemy search URL (fallback only)."""
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.udemy.com/courses/search/?q={encoded}&sort=relevance&ratings=4.0"
        if level:
            level_map = {"beginner": "beginner", "intermediate": "intermediate", "advanced": "expert"}
            if level.lower() in level_map:
                url += f"&instructional_level={level_map[level.lower()]}"
        return url
    
    def _build_search_fallback_url(
        self,
        platform: str,
        query: Optional[str],
        title: str,
        skill: str,
        level: str
    ) -> str:
        """Build a search URL as fallback."""
        search_query = self._build_search_query(title, query, skill, level, platform)
        
        if platform == "youtube":
            return self._build_youtube_search_url(search_query)
        elif platform == "coursera":
            return self._build_coursera_search_url(search_query, level)
        elif platform == "udemy":
            return self._build_udemy_search_url(search_query, level)
        
        return self._build_youtube_search_url(search_query)
    
    # ==================== Text Matching ====================
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _similarity_score(self, text_a: str, text_b: str) -> float:
        """
        Calculate similarity between two texts.
        Returns 0.0 to 1.0.
        """
        norm_a = self._normalize_text(text_a)
        norm_b = self._normalize_text(text_b)
        
        if not norm_a or not norm_b:
            return 0.0
        
        # Token overlap
        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())
        
        if not tokens_a or not tokens_b:
            return 0.0
        
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Substring bonus
        substring_bonus = 0.0
        if norm_a in norm_b or norm_b in norm_a:
            substring_bonus = 0.3
        
        return min(1.0, jaccard + substring_bonus)
    
    def _find_best_curated_match(
        self,
        candidate: Dict[str, Any],
        curated_candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best curated match for a candidate.
        
        Matching criteria:
        - Same platform
        - Similar title
        - Same or adjacent level
        """
        candidate_title = candidate.get("title", "")
        candidate_platform = self._normalize_platform(candidate.get("platform", ""))
        
        if not candidate_title or not candidate_platform:
            return None
        
        best_match = None
        best_score = 0.4  # Minimum threshold
        
        for curated in curated_candidates:
            # Must be same platform
            if self._normalize_platform(curated.get("platform", "")) != candidate_platform:
                continue
            
            curated_title = curated.get("title", "")
            similarity = self._similarity_score(candidate_title, curated_title)
            
            # Boost for adjacent level match
            if not curated.get("adjacent_level"):
                similarity += 0.1
            
            if similarity > best_score:
                best_score = similarity
                best_match = curated
        
        return best_match
    
    # ==================== Candidate Processing ====================
    
    def _process_curated_candidate(
        self,
        raw: Dict[str, Any],
        skill: str,
        level: str
    ) -> Optional[RecommendationCandidate]:
        """Process a curated resource into a candidate."""
        try:
            platform = self._normalize_platform(raw.get("platform", ""))
            if not platform:
                return None
            
            title = raw.get("title", "").strip()
            url = raw.get("url", "").strip()
            
            if not title or not url:
                return None
            
            # Validate it's a direct URL
            if not self._is_direct_course_url(url, platform):
                logger.warning(f"Curated URL is not direct: {url}")
                # Still use it but mark appropriately
            
            return RecommendationCandidate(
                title=title,
                platform=platform,
                url=url,
                url_type=raw.get("url_type", "direct"),
                description=raw.get("description", ""),
                reason=raw.get("reason", ""),
                difficulty=raw.get("difficulty", level).lower() if raw.get("difficulty") else level,
                source=raw.get("source", "curated"),
                is_free=raw.get("is_free", platform == "youtube"),
                duration_hours=raw.get("duration_hours"),
                rating=raw.get("rating")
            )
        except Exception as e:
            logger.warning(f"Failed to process curated candidate: {e}")
            return None
    
    def _process_gemini_candidate(
        self,
        raw: Dict[str, Any],
        skill: str,
        level: str,
        curated_for_matching: List[Dict[str, Any]]
    ) -> Optional[RecommendationCandidate]:
        """
        Process a Gemini recommendation.
        
        If Gemini provides a valid direct URL, use it.
        Otherwise, try to match to a curated resource.
        As last resort, create a search fallback.
        """
        try:
            platform = self._normalize_platform(raw.get("platform", ""))
            if not platform:
                return None
            
            title = raw.get("title", "").strip()
            url = raw.get("url", "").strip()
            query = raw.get("query", "")
            
            if not title:
                return None
            
            # Check if Gemini provided a valid direct URL
            if url and self._is_valid_platform_url(url, platform):
                if self._is_direct_course_url(url, platform):
                    # Gemini gave us a good direct URL!
                    return RecommendationCandidate(
                        title=title,
                        platform=platform,
                        url=url,
                        url_type="direct",
                        description=raw.get("description", ""),
                        reason=raw.get("reason", ""),
                        difficulty=raw.get("difficulty", level).lower() if raw.get("difficulty") else level,
                        source="gemini",
                        is_free=raw.get("is_free", platform == "youtube"),
                        duration_hours=raw.get("duration_hours"),
                        query=query
                    )
            
            # Try to match to a curated resource
            curated_match = self._find_best_curated_match(raw, curated_for_matching)
            if curated_match:
                return RecommendationCandidate(
                    title=curated_match.get("title", title),
                    platform=platform,
                    url=curated_match.get("url", ""),
                    url_type="direct",
                    description=curated_match.get("description", raw.get("description", "")),
                    reason=raw.get("reason", curated_match.get("reason", "")),
                    difficulty=curated_match.get("difficulty", level).lower() if curated_match.get("difficulty") else level,
                    source="resolved_curated",
                    is_free=curated_match.get("is_free", platform == "youtube"),
                    duration_hours=curated_match.get("duration_hours"),
                    query=query
                )
            
            # Fallback to search URL
            search_url = self._build_search_fallback_url(platform, query, title, skill, level)
            return RecommendationCandidate(
                title=title,
                platform=platform,
                url=search_url,
                url_type="search",
                description=raw.get("description", ""),
                reason=raw.get("reason", ""),
                difficulty=raw.get("difficulty", level).lower() if raw.get("difficulty") else level,
                source="fallback_search",
                is_free=raw.get("is_free", platform == "youtube"),
                duration_hours=raw.get("duration_hours"),
                query=query or self._build_search_query(title, None, skill, level, platform)
            )
            
        except Exception as e:
            logger.warning(f"Failed to process Gemini candidate: {e}")
            return None
    
    def _create_search_fallback(
        self,
        skill: str,
        level: str,
        platform: str,
        index: int
    ) -> RecommendationCandidate:
        """Create a search-based fallback recommendation."""
        modifiers = get_level_modifiers(level)
        skill_title = skill.title()
        
        titles = [
            f"{skill_title} {modifiers[0].title()} Tutorial",
            f"{skill_title} Complete Course",
            f"Learn {skill_title} - {modifiers[0].title()}",
        ]
        
        title = titles[index % len(titles)]
        query = f"{skill} {modifiers[0]} tutorial complete course"
        
        return RecommendationCandidate(
            title=title,
            platform=platform,
            url=self._build_search_fallback_url(platform, query, title, skill, level),
            url_type="search",
            description=f"{level.title()}-level {skill} learning resource",
            reason=f"Search results for {skill} {level} content",
            difficulty=level,
            source="fallback_search",
            is_free=platform == "youtube",
            query=query
        )
    
    # ==================== YouTube API Integration ====================
    
    def _load_youtube_api_videos(
        self,
        skill: str,
        level: str,
        limit: int = 3
    ) -> List[RecommendationCandidate]:
        """
        Fetch verified videos from YouTube Data API.
        
        This is the gold standard - 100% working links.
        Uses Gemini to generate optimal search queries, then YouTube API to get real videos.
        """
        youtube_client = get_youtube_client()
        
        if not youtube_client.is_available():
            logger.info("YouTube API not configured, skipping API lookup")
            return []
        
        candidates = []
        
        try:
            # Use Gemini to generate optimized search queries
            gemini_client = get_client()
            search_queries = gemini_client.generate_youtube_search_queries(
                skill=skill,
                level=level,
                num_queries=min(limit, 3)
            )
            
            if not search_queries:
                # Fallback to simple query construction
                level_terms = {
                    "beginner": "tutorial for beginners",
                    "intermediate": "tutorial intermediate",
                    "advanced": "advanced tutorial"
                }
                search_queries = [f"{skill} {level_terms.get(level.lower(), 'tutorial')}"]
            
            logger.info(f"YouTube API: Searching with {len(search_queries)} queries")
            
            seen_video_ids = set()
            
            for query in search_queries:
                videos = youtube_client.search_videos(
                    query=query,
                    max_results=2,
                    video_duration="medium"  # Prefer tutorial-length videos
                )
                
                for video in videos:
                    # Skip duplicates
                    if video.video_id in seen_video_ids:
                        continue
                    seen_video_ids.add(video.video_id)
                    
                    candidate = RecommendationCandidate(
                        title=video.title,
                        platform="youtube",
                        url=video.url,
                        url_type="direct",
                        description=video.description,
                        reason=f"Verified video from {video.channel_name}",
                        difficulty=level,
                        source="youtube_api",
                        is_free=True,
                        query=query
                    )
                    candidates.append(candidate)
                    
                    if len(candidates) >= limit:
                        break
                
                if len(candidates) >= limit:
                    break
            
            logger.info(f"YouTube API returned {len(candidates)} verified videos")
            return candidates
            
        except Exception as e:
            logger.warning(f"YouTube API error: {e}")
            return []
    
    # ==================== Scoring ====================
    
    def _score_candidate(
        self,
        candidate: RecommendationCandidate,
        skill: str,
        level: str,
        platform_counts: Optional[Dict[str, int]] = None
    ) -> float:
        """
        Score a candidate. Higher = better.
        
        YouTube API verified links score highest.
        Direct links score much higher than search links.
        """
        score = 0.0
        
        # URL type is the biggest factor
        if candidate.url_type == "direct":
            score += 10.0
        else:
            score -= 6.0  # Search fallback penalty
        
        # Source scoring - YouTube API is highest
        source_scores = {
            "youtube_api": 10.0,  # Verified via YouTube API - guaranteed to work
            "curated": 8.0,
            "gemini": 7.0,  # Gemini with valid direct URL
            "resolved_curated": 5.0,
            "generic_curated": 3.0,
            "fallback_search": -2.0,
            "unknown": 0.0
        }
        score += source_scores.get(candidate.source, 0.0)
        
        # Level alignment
        if candidate.difficulty.lower() == level.lower():
            score += 3.0
        elif level == "intermediate" and candidate.difficulty in ["beginner", "advanced"]:
            score += 1.0
        
        # Platform diversity
        if platform_counts:
            count = platform_counts.get(candidate.platform, 0)
            if count == 0:
                score += 2.0  # Fill missing platform
            elif count >= 2:
                score -= 1.0  # Reduce over-representation
        
        # Quality indicators
        if candidate.duration_hours:
            if 1 <= candidate.duration_hours <= 10:
                score += 1.0  # Reasonable length
        
        if candidate.is_free:
            score += 0.5
        
        # Penalties
        if not candidate.title:
            score -= 5.0
        
        return score
    
    def _dedupe_recommendations(
        self,
        candidates: List[RecommendationCandidate]
    ) -> List[RecommendationCandidate]:
        """Remove duplicates, preferring direct links."""
        seen_urls = set()
        seen_titles = set()
        deduped = []
        
        # Sort by score first so we keep the best version
        sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
        
        for candidate in sorted_candidates:
            # Check URL uniqueness
            if candidate.url in seen_urls:
                continue
            
            # Check title similarity
            norm_title = self._normalize_text(candidate.title)
            title_key = f"{candidate.platform}:{norm_title[:40]}"
            if title_key in seen_titles:
                continue
            
            seen_urls.add(candidate.url)
            seen_titles.add(title_key)
            deduped.append(candidate)
        
        return deduped
    
    def _rebalance_platform_diversity(
        self,
        candidates: List[RecommendationCandidate],
        limit: int
    ) -> List[RecommendationCandidate]:
        """Ensure platform diversity while prioritizing direct links."""
        if len(candidates) <= limit:
            return candidates
        
        # Separate by url_type first
        direct_by_platform: Dict[str, List[RecommendationCandidate]] = {
            "youtube": []
        }
        search_by_platform: Dict[str, List[RecommendationCandidate]] = {
            "youtube": []
        }
        
        for c in candidates:
            if c.platform in direct_by_platform:
                if c.url_type == "direct":
                    direct_by_platform[c.platform].append(c)
                else:
                    search_by_platform[c.platform].append(c)
        
        result = []
        
        # First pass: Add direct links from YouTube
        for platform in ["youtube"]:
            if direct_by_platform[platform] and len(result) < limit:
                result.append(direct_by_platform[platform].pop(0))
        
        # Second pass: Fill with remaining direct links
        remaining_direct = []
        for pl in direct_by_platform.values():
            remaining_direct.extend(pl)
        remaining_direct.sort(key=lambda x: x.score, reverse=True)
        
        for c in remaining_direct:
            if len(result) >= limit:
                break
            result.append(c)
        
        # Third pass: Only use search fallbacks if we still need more
        if len(result) < limit:
            for platform in ["youtube"]:
                if search_by_platform[platform] and len(result) < limit:
                    result.append(search_by_platform[platform].pop(0))
        
        return result
    
    # ==================== Main Pipeline ====================
    
    def get_recommendations(
        self,
        skill: str,
        level: SkillLevel,
        filter_options: Optional[ResourceFilter] = None,
        preferred_modalities: Optional[List[LearningModality]] = None,
        time_availability_hours: Optional[float] = None,
        interests: Optional[str] = None,
        limit: int = 6
    ) -> Tuple[List[ResourceRecommendation], Dict[str, Any]]:
        """
        Get recommendations using verified-link-first pipeline.
        
        Pipeline:
        1. YouTube API verified videos (100% working - highest priority)
        2. Curated direct-link resources
        3. Gemini recommendations (validated/resolved)
        4. Generic direct resources
        5. Search fallbacks (last resort)
        6. Score, dedupe, and rebalance
        """
        level_str = level.value if isinstance(level, SkillLevel) else level
        
        logger.info(f"Starting verified-link-first pipeline for {skill}/{level_str}")
        
        candidates: List[RecommendationCandidate] = []
        meta = {
            "skill": skill,
            "level": level_str,
            "youtube_api_used": False,
            "curated_used": False,
            "gemini_used": False,
            "resolved_curated_used": False,
            "generic_curated_used": False,
            "search_fallback_used": False,
            "direct_count": 0,
            "search_count": 0,
            "total_candidates": 0,
            "total_returned": 0
        }
        
        # 1. YouTube API verified videos (highest priority - 100% working)
        youtube_videos = self._load_youtube_api_videos(skill, level_str, limit=3)
        if youtube_videos:
            candidates.extend(youtube_videos)
            meta["youtube_api_used"] = True
            logger.info(f"Added {len(youtube_videos)} YouTube API verified videos")
        
        # 2. Load curated direct-link resources
        curated = get_curated_resources(skill, level_str)
        curated_for_matching = get_all_curated_for_matching(skill, level_str)
        
        for raw in curated:
            candidate = self._process_curated_candidate(raw, skill, level_str)
            if candidate:
                candidates.append(candidate)
                meta["curated_used"] = True
        
        logger.info(f"Loaded {len(curated)} curated direct-link resources")
        
        # 3. Fetch and process Gemini recommendations
        gemini_raw = self._load_gemini_candidates(skill, level_str, limit)
        
        for raw in gemini_raw:
            candidate = self._process_gemini_candidate(raw, skill, level_str, curated_for_matching)
            if candidate:
                candidates.append(candidate)
                if candidate.source == "gemini":
                    meta["gemini_used"] = True
                elif candidate.source == "resolved_curated":
                    meta["resolved_curated_used"] = True
                elif candidate.source == "fallback_search":
                    meta["search_fallback_used"] = True
        
        logger.info(f"Processed {len(gemini_raw)} Gemini recommendations")
        
        # 4. Add generic direct resources if we need more
        direct_count = sum(1 for c in candidates if c.url_type == "direct")
        if direct_count < limit:
            generic = get_generic_direct_resources(level_str)
            for raw in generic:
                candidate = self._process_curated_candidate(raw, skill, level_str)
                if candidate:
                    candidate.source = "generic_curated"
                    candidates.append(candidate)
                    meta["generic_curated_used"] = True
        
        # 5. Add search fallbacks only if still short
        if len(candidates) < limit:
            platforms = ["youtube"]
            for i, platform in enumerate(platforms * 2):
                if len(candidates) >= limit * 2:
                    break
                fallback = self._create_search_fallback(skill, level_str, platform, i)
                candidates.append(fallback)
                meta["search_fallback_used"] = True
        
        meta["total_candidates"] = len(candidates)
        
        # 5. Score all candidates
        platform_counts: Dict[str, int] = {}
        for c in candidates:
            c.score = self._score_candidate(c, skill, level_str, platform_counts)
            platform_counts[c.platform] = platform_counts.get(c.platform, 0) + 1
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # 6. Dedupe
        deduped = self._dedupe_recommendations(candidates)
        logger.info(f"Deduped to {len(deduped)} candidates")
        
        # 7. Rebalance for platform diversity
        balanced = self._rebalance_platform_diversity(deduped, limit)
        
        # 8. Apply filters
        filtered = self._apply_filters(balanced, filter_options)
        
        # 8b. YouTube only - drop any non-YouTube that might have slipped through
        filtered = [c for c in filtered if c.platform == "youtube"]
        
        # 9. Convert to response
        recommendations = []
        for candidate in filtered[:limit]:
            rec = self._to_resource_recommendation(candidate)
            recommendations.append(rec)
            if candidate.url_type == "direct":
                meta["direct_count"] += 1
            else:
                meta["search_count"] += 1
        
        meta["total_returned"] = len(recommendations)
        
        logger.info(f"Returning {len(recommendations)} recommendations "
                   f"(direct={meta['direct_count']}, search={meta['search_count']})")
        
        return recommendations, meta
    
    def _load_gemini_candidates(
        self,
        skill: str,
        level: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch recommendations from Gemini."""
        client = get_client()
        
        try:
            raw = client.get_course_recommendations(
                skill=skill,
                level=level,
                preferred_modalities=["video"],
                num_recommendations=limit
            )
            
            for rec in raw:
                rec["source"] = "gemini"
            
            logger.info(f"Received {len(raw)} Gemini recommendations")
            return raw
            
        except Exception as e:
            logger.warning(f"Gemini failed: {e}")
            return []
    
    def _apply_filters(
        self,
        candidates: List[RecommendationCandidate],
        filter_options: Optional[ResourceFilter]
    ) -> List[RecommendationCandidate]:
        """Apply user filters."""
        if not filter_options:
            return candidates
        
        filtered = []
        for c in candidates:
            if filter_options.platforms:
                if c.platform not in [p.value for p in filter_options.platforms]:
                    continue
            
            if filter_options.free_only and not c.is_free:
                continue
            
            if filter_options.max_duration_hours and c.duration_hours:
                if c.duration_hours > filter_options.max_duration_hours:
                    continue
            
            filtered.append(c)
        
        return filtered
    
    def _to_resource_recommendation(
        self,
        candidate: RecommendationCandidate
    ) -> ResourceRecommendation:
        """Convert to API response model."""
        try:
            platform = Platform(candidate.platform)
        except ValueError:
            platform = Platform.YOUTUBE
        
        try:
            difficulty = SkillLevel(candidate.difficulty)
        except ValueError:
            difficulty = SkillLevel.INTERMEDIATE
        
        return ResourceRecommendation(
            resource_id=f"{candidate.platform}_{hash(candidate.url) % 100000}",
            title=candidate.title,
            platform=platform,
            url=candidate.url,
            url_type=candidate.url_type,
            embed_url=None,
            topic_coverage=[],
            difficulty=difficulty,
            duration_hours=candidate.duration_hours,
            rating=candidate.rating,
            is_free=candidate.is_free,
            price="Free" if candidate.is_free else None,
            source=candidate.source,
            affiliate_link=None,
            snippet_start=None,
            snippet_end=None,
            relevance_score=min(1.0, max(0.0, (candidate.score + 10) / 30))
        )


# Module singleton
recommendation_service = RecommendationService()
