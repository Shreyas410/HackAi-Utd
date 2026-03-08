"""
Skill level classification service.
Uses Gemini API exclusively for classification (no local threshold logic).
Maps to Dreyfus model: Beginner (Novice), Intermediate (Competent), Advanced (Proficient/Expert).
"""

from typing import Dict, Any, List, Optional, Tuple
from ..models.schemas import SkillLevel, LevelExplanation, QuestionnaireAnswer
from ..config import settings
from .gemini_client import get_client


class ClassificationService:
    """
    Service for classifying learner skill levels.
    
    IMPORTANT: Classification is performed by Gemini API.
    No local threshold logic is applied - Gemini's response is used directly.
    """
    
    def classify(
        self,
        answers: List[QuestionnaireAnswer],
        skill: str
    ) -> Tuple[SkillLevel, LevelExplanation]:
        """
        Classify the learner's skill level using Gemini API.
        
        The questionnaire responses are formatted and sent to Gemini,
        which returns a classification based on the Dreyfus model.
        
        Args:
            answers: List of questionnaire answers
            skill: The skill being assessed
        
        Returns:
            Tuple of (SkillLevel, LevelExplanation)
        
        Note:
            Classification is performed entirely by Gemini.
            No local threshold logic is applied.
        """
        # Convert answers to dictionary
        answers_dict = {a.question_id: a.answer for a in answers}
        
        # Get Gemini client and classify
        client = get_client()
        
        try:
            result = client.classify_skill_level(skill, answers_dict)
            
            # Extract level from Gemini response
            level_str = result.get("level", "beginner").lower()
            level = SkillLevel(level_str)
            
            # Build explanation from Gemini's reasoning
            reasoning = result.get("reasoning", [])
            confidence = result.get("confidence", 0.8)
            
            # Add Dreyfus model context to factors
            factors = list(reasoning)
            factors.append(f"Classification: {level.value.title()} (Dreyfus Model)")
            factors.append("Classified by Gemini AI analysis")
            
            explanation = LevelExplanation(
                level=level,
                confidence=float(confidence),
                factors=factors,
                can_challenge=True
            )
            
            return level, explanation
            
        except Exception as e:
            # If Gemini fails, return a safe default with explanation
            # This should rarely happen in production
            return SkillLevel.BEGINNER, LevelExplanation(
                level=SkillLevel.BEGINNER,
                confidence=0.5,
                factors=[
                    f"Classification service error: {str(e)}",
                    "Defaulting to Beginner level for safety",
                    "Please retry or contact support"
                ],
                can_challenge=True
            )
    
    def adjust_level_after_quiz(
        self,
        current_level: SkillLevel,
        quiz_score: float,
        quiz_difficulty: SkillLevel
    ) -> Tuple[Optional[SkillLevel], str]:
        """
        Potentially adjust level based on quiz performance.
        
        This uses rule-based logic (not Gemini) since it's based on
        concrete quiz scores rather than subjective assessment.
        
        Args:
            current_level: Current assigned level
            quiz_score: Quiz score as percentage (0-100)
            quiz_difficulty: Difficulty level of the quiz
        
        Returns:
            Tuple of (new_level or None if unchanged, explanation)
        """
        upgrade_threshold = settings.upgrade_score_threshold * 100  # 85%
        downgrade_threshold = settings.downgrade_score_threshold * 100  # 40%
        
        # Upgrade logic
        if quiz_score >= upgrade_threshold:
            if current_level == SkillLevel.BEGINNER and quiz_difficulty == SkillLevel.BEGINNER:
                return SkillLevel.INTERMEDIATE, f"Excellent score ({quiz_score:.0f}%)! Upgrading to Intermediate."
            elif current_level == SkillLevel.INTERMEDIATE and quiz_difficulty == SkillLevel.INTERMEDIATE:
                return SkillLevel.ADVANCED, f"Outstanding performance ({quiz_score:.0f}%)! Upgrading to Advanced."
        
        # Downgrade logic
        if quiz_score < downgrade_threshold:
            if current_level == SkillLevel.ADVANCED and quiz_difficulty == SkillLevel.ADVANCED:
                return SkillLevel.INTERMEDIATE, f"Score ({quiz_score:.0f}%) suggests Intermediate might be more appropriate."
            elif current_level == SkillLevel.INTERMEDIATE and quiz_difficulty == SkillLevel.INTERMEDIATE:
                return SkillLevel.BEGINNER, f"Score ({quiz_score:.0f}%) suggests starting with Beginner content."
        
        return None, f"Quiz score: {quiz_score:.0f}%. Current level confirmed."


classification_service = ClassificationService()
