"""
Pydantic schemas for API request/response validation.
All JSON formats documented with examples.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime
import uuid


# ============== Enums ==============

class SkillLevel(str, Enum):
    """Learner skill levels based on Dreyfus model."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuestionType(str, Enum):
    """Types of questionnaire/quiz questions."""
    MULTIPLE_CHOICE = "multiple_choice"
    RATING = "rating"
    TEXT = "text"
    MULTI_SELECT = "multi_select"


class LearningModality(str, Enum):
    """Preferred learning methods."""
    VIDEO = "video"
    ARTICLES = "articles"
    INTERACTIVE = "interactive_exercises"
    PROJECTS = "hands_on_projects"
    BOOKS = "books"
    MENTORSHIP = "mentorship"


class Platform(str, Enum):
    """Supported resource platforms."""
    YOUTUBE = "youtube"
    COURSERA = "coursera"
    UDEMY = "udemy"


# ============== Session Schemas ==============

class StartSessionRequest(BaseModel):
    """Request to start a new learning session."""
    skill: str = Field(..., description="The skill the user wants to learn", example="Python programming")

    class Config:
        json_schema_extra = {
            "example": {
                "skill": "Python programming"
            }
        }


class QuestionOption(BaseModel):
    """An option for a question."""
    value: str = Field(..., description="The value/id of the option")
    label: str = Field(..., description="Display text for the option")
    

class Question(BaseModel):
    """A questionnaire or quiz question."""
    question_id: str = Field(..., description="Unique identifier for the question")
    type: QuestionType = Field(..., description="Type of question")
    prompt: str = Field(..., description="The question text")
    options: Optional[List[QuestionOption]] = Field(None, description="Available options")
    category: Optional[str] = Field(None, description="Category/section of the question")
    required: bool = Field(True, description="Whether the question must be answered")
    sub_skill: Optional[str] = Field(None, description="Related sub-skill for self-assessment questions")

    class Config:
        json_schema_extra = {
            "example": {
                "question_id": "self_rating_1",
                "type": "rating",
                "prompt": "Rate your confidence with Python basic syntax (1-5)",
                "options": [
                    {"value": "1", "label": "No knowledge"},
                    {"value": "2", "label": "Basic awareness"},
                    {"value": "3", "label": "Can apply with guidance"},
                    {"value": "4", "label": "Confident"},
                    {"value": "5", "label": "Expert"},
                    {"value": "na", "label": "Not applicable"}
                ],
                "category": "self_assessment",
                "required": True,
                "sub_skill": "basic_syntax"
            }
        }


class StartSessionResponse(BaseModel):
    """Response after starting a learning session."""
    session_id: str = Field(..., description="Unique session identifier")
    skill: str = Field(..., description="The skill being learned")
    questionnaire: List[Question] = Field(..., description="Initial questionnaire")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123-def456",
                "skill": "Python programming",
                "questionnaire": [],
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


# ============== Questionnaire Response Schemas ==============

class QuestionnaireAnswer(BaseModel):
    """A single answer to a questionnaire question."""
    question_id: str = Field(..., description="ID of the question being answered")
    answer: Any = Field(..., description="The answer value (string, number, or list)")


class SubmitQuestionnaireRequest(BaseModel):
    """Request to submit questionnaire responses."""
    session_id: str = Field(..., description="The session ID")
    answers: List[QuestionnaireAnswer] = Field(..., description="List of answers")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123-def456",
                "answers": [
                    {"question_id": "job_title", "answer": "Software Developer"},
                    {"question_id": "experience_years", "answer": "3"},
                    {"question_id": "self_rating_syntax", "answer": "4"}
                ]
            }
        }


class LevelExplanation(BaseModel):
    """Explanation of how the skill level was determined."""
    level: SkillLevel = Field(..., description="Assigned skill level")
    confidence: float = Field(..., description="Confidence score 0-1")
    factors: List[str] = Field(..., description="Factors that influenced the decision")
    can_challenge: bool = Field(True, description="Whether the user can challenge this assessment")


class SubmitQuestionnaireResponse(BaseModel):
    """Response after submitting questionnaire."""
    session_id: str
    assigned_level: SkillLevel
    explanation: LevelExplanation
    next_step: str = Field(default="diagnostic_quiz", description="The next step in the learning journey")


# ============== Quiz Schemas ==============

class QuizQuestion(BaseModel):
    """A quiz question with answer options."""
    question_id: str
    type: QuestionType
    prompt: str
    options: Optional[List[QuestionOption]] = None
    difficulty: SkillLevel
    points: int = Field(default=1, description="Points for correct answer")
    time_limit_seconds: Optional[int] = Field(None, description="Optional time limit")
    correct_answer: Optional[str] = Field(None, description="Correct answer value (hidden from user in response)")
    explanation: Optional[str] = Field(None, description="Explanation for the correct answer")


class GetQuizResponse(BaseModel):
    """Response containing the diagnostic quiz."""
    session_id: str
    quiz_id: str
    skill: str
    target_level: SkillLevel
    questions: List[QuizQuestion]
    total_points: int
    time_limit_minutes: Optional[int] = None


class QuizAnswer(BaseModel):
    """A single quiz answer."""
    question_id: str
    answer: Any


class SubmitQuizRequest(BaseModel):
    """Request to submit quiz answers."""
    session_id: str
    quiz_id: str
    answers: List[QuizAnswer]


class QuizResult(BaseModel):
    """Result of a single quiz question."""
    question_id: str
    correct: bool
    points_earned: int
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None


class SubmitQuizResponse(BaseModel):
    """Response after submitting quiz."""
    session_id: str
    quiz_id: str
    score: float = Field(..., description="Score as percentage 0-100")
    score_percentage: float = Field(default=0, description="Alias for score percentage")
    skill_score: int = Field(..., ge=1, le=10, description="Overall skill score from 1-10")
    points_earned: int
    total_points: int
    results: List[QuizResult]
    level_updated: bool
    new_level: Optional[SkillLevel] = None
    feedback: str


# ============== Scenario Practice Schemas ==============

class ScenarioAction(BaseModel):
    """A possible action in a scenario."""
    action_id: str
    description: str
    is_optimal: Optional[bool] = Field(None, description="Hidden from user")


class ScenarioNode(BaseModel):
    """A node/decision point in a scenario."""
    node_id: str
    narrative: str = Field(..., description="The scenario description at this point")
    actions: List[ScenarioAction]
    is_terminal: bool = Field(False, description="Whether this ends the scenario")


class ScenarioResponse(BaseModel):
    """Response containing a practice scenario."""
    session_id: str
    scenario_id: str
    title: str
    skill: str
    difficulty: SkillLevel
    learning_outcomes: List[str]
    current_node: ScenarioNode


class ScenarioActionRequest(BaseModel):
    """Request to take an action in a scenario."""
    session_id: str
    scenario_id: str
    node_id: str
    action_id: str


class ScenarioFeedback(BaseModel):
    """Feedback after taking a scenario action."""
    action_taken: str
    consequence: str
    feedback: str
    score_delta: int
    next_node: Optional[ScenarioNode] = None
    scenario_complete: bool = False
    final_score: Optional[int] = None


# ============== Concept Map Schemas ==============

class ConceptMapRequest(BaseModel):
    """Request for a concept map."""
    skill: str = Field(..., description="The skill to get a concept map for")


class ConceptMapNode(BaseModel):
    """A node in the concept map."""
    id: str
    label: str
    level: Optional[SkillLevel] = None


class ConceptMapEdge(BaseModel):
    """An edge/relationship in the concept map."""
    source: str
    target: str
    relationship: str = Field(default="relates_to")


class ConceptMapResponse(BaseModel):
    """Response containing concept map data."""
    skill: str
    image_url: Optional[str] = Field(None, description="URL to pre-generated image")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image")
    nodes: List[ConceptMapNode] = Field(default_factory=list)
    edges: List[ConceptMapEdge] = Field(default_factory=list)
    format: str = Field(default="png")


# ============== Resource Recommendation Schemas ==============

class ResourceFilter(BaseModel):
    """Filters for resource recommendations."""
    session_id: str
    platforms: Optional[List[Platform]] = None
    max_duration_hours: Optional[float] = None
    free_only: bool = False
    modalities: Optional[List[LearningModality]] = None


class ResourceRecommendation(BaseModel):
    """A recommended learning resource."""
    resource_id: str
    title: str
    platform: Platform
    url: str
    embed_url: Optional[str] = Field(None, description="Embeddable URL (for YouTube)")
    topic_coverage: List[str]
    difficulty: SkillLevel
    duration_hours: Optional[float] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    is_free: bool
    price: Optional[str] = None
    affiliate_link: Optional[str] = None
    snippet_start: Optional[int] = Field(None, description="Start time in seconds (YouTube)")
    snippet_end: Optional[int] = Field(None, description="End time in seconds (YouTube)")
    relevance_score: float = Field(..., description="How well it matches the learner profile")


class ResourceRecommendationResponse(BaseModel):
    """Response with resource recommendations."""
    session_id: str
    learner_level: SkillLevel
    recommendations: List[ResourceRecommendation]
    total_available: int


# ============== Data Privacy Schemas ==============

class DeleteDataRequest(BaseModel):
    """Request to delete user data."""
    session_id: str
    confirmation: bool = Field(..., description="Must be True to confirm deletion")


class DeleteDataResponse(BaseModel):
    """Response after data deletion."""
    success: bool
    message: str
    deleted_at: datetime


class ChallengeAssessmentRequest(BaseModel):
    """Request to challenge the assigned level."""
    session_id: str
    requested_level: SkillLevel
    reason: Optional[str] = None


class ChallengeAssessmentResponse(BaseModel):
    """Response to level challenge."""
    session_id: str
    challenge_accepted: bool
    new_level: Optional[SkillLevel] = None
    additional_quiz_required: bool = False
    message: str


# ============== Health Check ==============

class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
