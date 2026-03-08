"""
Sentiment Analysis Service for YouTube video comments.

Uses Gemini to classify comments as positive/negative/neutral,
then calculates quality scores and confidence levels.

Scoring Rules:
- Score: 0-5 based on sentiment distribution
- Confidence: 0-1 based on comment volume
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .gemini_client import get_client
from .youtube_client import YouTubeComment

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Result of sentiment analysis on a video's comments."""
    score: float  # 0-5
    summary: str  # e.g., "Good (3.8/5)"
    confidence: float  # 0-1
    positive_count: int
    negative_count: int
    neutral_count: int
    total_comments: int
    comments_available: bool = True
    note: Optional[str] = None


class SentimentAnalyzer:
    """
    Analyzes YouTube video comments for sentiment.
    
    Uses Gemini for comment classification, then applies
    scoring rules to generate quality metrics.
    """
    
    # Score thresholds for summary labels
    SCORE_LABELS = [
        (4.5, "Excellent"),
        (3.5, "Good"),
        (2.5, "Average"),
        (1.5, "Below Average"),
        (0.0, "Poor")
    ]
    
    # Confidence based on comment count
    CONFIDENCE_THRESHOLDS = [
        (100, 0.95),
        (50, 0.85),
        (20, 0.75),
        (10, 0.60),
        (1, 0.40),
        (0, 0.10)
    ]
    
    def __init__(self):
        self.gemini_client = get_client()
    
    def analyze_comments(
        self,
        comments: List[YouTubeComment],
        comments_available: bool = True
    ) -> SentimentResult:
        """
        Analyze a list of comments and return sentiment metrics.
        
        Args:
            comments: List of YouTubeComment objects
            comments_available: Whether comments were available for the video
        
        Returns:
            SentimentResult with score, confidence, and breakdown
        """
        total_comments = len(comments)
        
        # Handle case where no comments
        if total_comments == 0:
            return SentimentResult(
                score=0.0,
                summary="No Data (0.0/5)",
                confidence=0.10,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                total_comments=0,
                comments_available=comments_available,
                note="No comments available for analysis" if not comments_available 
                     else "Video has no comments"
            )
        
        # Classify comments using Gemini
        positive, negative, neutral = self._classify_comments(comments)
        
        # Determine actual classified count (may be slightly less than total if some failed parsing)
        classified_count = positive + negative + neutral
        
        if classified_count == 0:
             return SentimentResult(
                score=0.0,
                summary="No Data (0.0/5)",
                confidence=0.10,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                total_comments=total_comments,
                comments_available=comments_available,
                note="Failed to classify any comments"
            )

        # Calculate raw score 
        # Tech tutorials get lots of neutral comments (questions, timestamps). We shouldn't punish videos for having long discussions.
        # So we base the score heavily on the positive vs negative ratio, essentially ignoring neutral comments.
        
        opinionated_count = positive + negative
        
        if opinionated_count == 0:
            # If the video has almost entirely "neutral" comments, the API failed to find strong opinions at all. Let's just grade on a relaxed curve.
            raw_score = 0.6 # 3.0 / 5.0
        else:
            # Ratio of positive vs all non-neutral comments
            base_sentiment = positive / opinionated_count
            
            # If there are no negative comments, it's a perfect score minus a tiny penalty for low engagement
            if negative == 0:
                raw_score = 0.95 + (positive / 100) * 0.05
            else:
                raw_score = base_sentiment
        
        # Convert to 5-point scale
        score = round(raw_score * 5, 1)
        
        # Get confidence based on comment count
        confidence = self._calculate_confidence(total_comments, positive, negative, neutral)
        
        # Generate summary label
        summary = self._get_score_label(score)
        
        # Add note if low confidence
        note = None
        if confidence < 0.6:
            note = "Low confidence due to limited comment data"
        elif not comments_available:
            note = "Comments were limited or restricted"
        
        return SentimentResult(
            score=score,
            summary=f"{summary} ({score}/5)",
            confidence=round(confidence, 2),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            total_comments=total_comments,
            comments_available=comments_available,
            note=note
        )
    
    def _classify_comments(
        self,
        comments: List[YouTubeComment]
    ) -> Tuple[int, int, int]:
        """
        Classify comments using Gemini.
        
        Returns tuple of (positive_count, negative_count, neutral_count)
        """
        if not comments:
            return 0, 0, 0
        
        # Prepare comments for batch classification. Limit to 50 for AI speed and reliability
        comment_texts = [c.text[:500] for c in comments[:50]]
        
        try:
            classifications = self._batch_classify(comment_texts)
            if not classifications:
                return self._simple_classify(comment_texts)
            
            positive = sum(1 for c in classifications if c == "positive")
            negative = sum(1 for c in classifications if c == "negative")
            neutral = len(classifications) - positive - negative
            
            return positive, negative, neutral
            
        except Exception as e:
            logger.error(f"Gemini classification failed: {e}")
            # Fallback to simple keyword-based classification
            return self._simple_classify(comment_texts)
    
    def _batch_classify(self, comments: List[str]) -> List[str]:
        """
        Use Gemini to classify comments in batch.
        """
        if not comments:
            return []
        
        # Build prompt for batch classification
        comments_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(comments)])
        
        prompt = f"""Classify each YouTube comment as positive, negative, or neutral.

CLASSIFICATION RULES:
- POSITIVE: praise, usefulness, clarity, recommendation, gratitude, strong approval, helpful content
- NEGATIVE: poor teaching, confusion, misleading title, outdated material, low quality, complaints, criticism
- NEUTRAL: factual remarks, timestamps, questions, unrelated observations, mixed statements

COMMENTS TO CLASSIFY:
{comments_text}

Return exactly {len(comments)} classifications. Do NOT stop early. You must output exactly {len(comments)} string elements."""

        try:
            if not getattr(self.gemini_client, 'model', None):
                return self._simple_classify_list(comments)
            response = self.gemini_client.model.generate_content(prompt)
            raw_text = (response.text or "").strip()
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if json_match:
                classifications = json.loads(json_match.group())
                
                # Validate and normalize
                valid_classes = {"positive", "negative", "neutral"}
                normalized = []
                for c in classifications:
                    c_lower = str(c).lower().strip()
                    if c_lower in valid_classes:
                        normalized.append(c_lower)
                    else:
                        normalized.append("neutral")
                
                # Pad if needed
                while len(normalized) < len(comments):
                    normalized.append("neutral")
                
                return normalized[:len(comments)]
            
            raise ValueError("Could not parse classification response")
            
        except Exception as e:
            logger.warning(f"Batch classification failed: {e}, using simple method")
            return self._simple_classify_list(comments)
    
    def _simple_classify(self, comments: List[str]) -> Tuple[int, int, int]:
        """Simple keyword-based fallback classification."""
        if not comments:
            return 0, 0, 0
            
        classifications = self._simple_classify_list(comments)
        positive = sum(1 for c in classifications if c == "positive")
        negative = sum(1 for c in classifications if c == "negative")
        neutral = len(classifications) - positive - negative
        return positive, negative, neutral
    
    def _simple_classify_list(self, comments: List[str]) -> List[str]:
        """Classify comments using simple keywords."""
        positive_words = {
            "great", "excellent", "amazing", "helpful", "thanks", "thank you",
            "perfect", "awesome", "love", "best", "clear", "good", "useful",
            "fantastic", "wonderful", "brilliant", "well done", "superb"
        }
        negative_words = {
            "bad", "terrible", "awful", "confusing", "waste", "boring",
            "useless", "poor", "wrong", "misleading", "outdated", "worst",
            "horrible", "disappointed", "hate", "dislike", "unclear"
        }
        
        results = []
        for comment in comments:
            comment_lower = comment.lower()
            
            pos_count = sum(1 for w in positive_words if w in comment_lower)
            neg_count = sum(1 for w in negative_words if w in comment_lower)
            
            if pos_count > neg_count:
                results.append("positive")
            elif neg_count > pos_count:
                results.append("negative")
            elif pos_count > 0 and neg_count > 0:
                results.append("neutral")
            else:
                # If neither positive nor negative words are present, it's essentially blank/unhelpful
                # We can safely classify these as neutral, or just omit them from the core ratio
                results.append("neutral")
        
        return results
    
    def _calculate_confidence(
        self,
        total: int,
        positive: int,
        negative: int,
        neutral: int
    ) -> float:
        """
        Calculate confidence score based on comment volume and distribution.
        """
        # Base confidence from comment count
        base_confidence = 0.10
        for threshold, conf in self.CONFIDENCE_THRESHOLDS:
            if total >= threshold:
                base_confidence = conf
                break
        
        # Slight adjustment for very mixed results (harder to be confident)
        if total > 0:
            max_category = max(positive, negative, neutral)
            dominance = max_category / total
            
            # If no category dominates (very mixed), reduce confidence slightly
            if dominance < 0.4:
                base_confidence *= 0.9
        
        return min(base_confidence, 1.0)
    
    def _get_score_label(self, score: float) -> str:
        """Get label for a score."""
        for threshold, label in self.SCORE_LABELS:
            if score >= threshold:
                return label
        return "Poor"


@dataclass
class VideoComparison:
    """Result of comparing two videos."""
    recommended_video: Dict[str, Any]
    comparison_video: Dict[str, Any]
    comparison_result: Dict[str, Any]


class VideoComparer:
    """
    Compares two YouTube videos based on sentiment and engagement.
    """
    
    def compare(
        self,
        video1: Dict[str, Any],
        video2: Dict[str, Any]
    ) -> VideoComparison:
        """
        Compare two analyzed videos.
        
        Args:
            video1: First video analysis dict (recommended)
            video2: Second video analysis dict (comparison)
        
        Returns:
            VideoComparison with detailed comparison
        """
        sent1 = video1.get("sentiment", {})
        sent2 = video2.get("sentiment", {})
        
        score1 = sent1.get("score", 0)
        score2 = sent2.get("score", 0)
        conf1 = sent1.get("confidence", 0)
        conf2 = sent2.get("confidence", 0)
        
        score_diff = round(abs(score1 - score2), 1)
        
        # Determine winner
        better_video, reason, confidence_note = self._determine_winner(
            score1, score2, conf1, conf2, score_diff,
            video1.get("view_count", 0), video2.get("view_count", 0)
        )
        
        return VideoComparison(
            recommended_video=video1,
            comparison_video=video2,
            comparison_result={
                "better_video": better_video,
                "reason": reason,
                "score_difference": score_diff,
                "confidence_note": confidence_note
            }
        )
    
    def _determine_winner(
        self,
        score1: float,
        score2: float,
        conf1: float,
        conf2: float,
        score_diff: float,
        views1: int,
        views2: int
    ) -> Tuple[str, str, str]:
        """
        Determine which video is better and why.
        
        Returns: (winner, reason, confidence_note)
        """
        # Both low confidence
        if conf1 < 0.5 and conf2 < 0.5:
            return (
                "inconclusive",
                "Both videos have insufficient comment data for reliable comparison",
                "Very low confidence on both videos due to limited comments"
            )
        
        # Scores very close (within 0.3)
        if score_diff < 0.3:
            # Check if confidence differs significantly
            if abs(conf1 - conf2) > 0.2:
                higher_conf = "recommended_video" if conf1 > conf2 else "comparison_video"
                return (
                    higher_conf,
                    f"Scores are similar, but {higher_conf.replace('_', ' ')} has more reliable data",
                    f"Recommended: {conf1:.0%} confidence, Comparison: {conf2:.0%} confidence"
                )
            
            return (
                "inconclusive",
                "Both videos have very similar sentiment scores",
                "Difference too small to determine a clear winner"
            )
        
        # Clear score difference
        if score1 > score2:
            winner = "recommended_video"
            reason = f"Recommended video has better audience sentiment ({score1}/5 vs {score2}/5)"
        else:
            winner = "comparison_video"
            reason = f"Comparison video has better audience sentiment ({score2}/5 vs {score1}/5)"
        
        # Add confidence note
        if conf1 >= 0.75 and conf2 >= 0.75:
            confidence_note = "High confidence in both analyses"
        elif conf1 >= 0.75 or conf2 >= 0.75:
            higher = "recommended" if conf1 > conf2 else "comparison"
            confidence_note = f"The {higher} video has more reliable sentiment data"
        else:
            confidence_note = "Moderate confidence - results may vary with more comments"
        
        return winner, reason, confidence_note


# Module-level instances
_sentiment_analyzer: Optional[SentimentAnalyzer] = None
_video_comparer: Optional[VideoComparer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create the sentiment analyzer."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer


def get_video_comparer() -> VideoComparer:
    """Get or create the video comparer."""
    global _video_comparer
    if _video_comparer is None:
        _video_comparer = VideoComparer()
    return _video_comparer
