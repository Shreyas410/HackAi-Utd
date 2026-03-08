"""
Gemini API client with mock support for testing.
Centralizes all Gemini interactions for classification and recommendations.
"""

import json
import os
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod

from ..config import settings

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiClientBase(ABC):
    """Abstract base class for Gemini clients."""
    
    @abstractmethod
    def classify_skill_level(
        self,
        skill: str,
        questionnaire_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify learner's skill level based on questionnaire responses."""
        pass
    
    @abstractmethod
    def get_course_recommendations(
        self,
        skill: str,
        level: str,
        preferred_modalities: List[str],
        interests: Optional[str] = None,
        num_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """Get course recommendations from YouTube, Coursera, Udemy."""
        pass
    
    @abstractmethod
    def interpret_quiz_answer(
        self,
        question: str,
        expected_concepts: List[str],
        user_answer: str
    ) -> Dict[str, Any]:
        """Interpret free-form quiz answers for advanced quizzes."""
        pass

    @abstractmethod
    def generate_quiz_questions(
        self,
        skill: str,
        level: str,
        num_questions: int,
        topics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions dynamically using AI."""
        pass


class GeminiClient(GeminiClientBase):
    """
    Real Gemini API client.
    Requires GEMINI_API_KEY environment variable.
    """
    
    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed")
        
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def classify_skill_level(
        self,
        skill: str,
        questionnaire_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send questionnaire responses to Gemini for classification.
        
        Gemini classifies based on the Dreyfus model:
        - Beginner (Novice/Advanced Beginner)
        - Intermediate (Competent)
        - Advanced (Proficient/Expert)
        
        Returns:
            Dict with 'level', 'confidence', and 'reasoning'
        """
        formatted_responses = self._format_responses(questionnaire_responses)
        
        prompt = f"""You are an expert educational assessor. Based on the following questionnaire responses, 
classify the learner's skill level for "{skill}" using the Dreyfus Model of Skill Acquisition.

=== QUESTIONNAIRE RESPONSES ===
{formatted_responses}

=== CLASSIFICATION LEVELS ===
Map your assessment to one of these three levels:

1. BEGINNER (Dreyfus: Novice/Advanced Beginner)
   - Little to no practical experience
   - Relies on explicit rules and step-by-step instructions
   - Needs guidance to recognize relevant features
   - Difficulty prioritizing information

2. INTERMEDIATE (Dreyfus: Competent)
   - Has meaningful experience (1-3 years practical use)
   - Can plan and execute tasks independently
   - Applies rules flexibly based on context
   - Sees long-term goals and can troubleshoot

3. ADVANCED (Dreyfus: Proficient/Expert)
   - Extensive experience (3+ years)
   - Uses intuition and pattern recognition
   - Can teach and mentor others
   - Innovates and adapts to novel situations

=== REQUIRED OUTPUT FORMAT ===
Respond ONLY with valid JSON in this exact format:
{{
    "level": "beginner" | "intermediate" | "advanced",
    "confidence": <float 0.0-1.0>,
    "reasoning": [
        "<factor 1 that influenced your decision>",
        "<factor 2 that influenced your decision>",
        "<factor 3 that influenced your decision>"
    ]
}}

Analyze ALL responses holistically. Consider self-ratings, experience, prior exposure, and goals together.
If data is ambiguous, lean toward the lower level to ensure appropriate content difficulty."""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            raise RuntimeError(f"Gemini classification failed: {e}")
    
    def get_course_recommendations(
        self,
        skill: str,
        level: str,
        preferred_modalities: List[str],
        interests: Optional[str] = None,
        num_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Ask Gemini to recommend personalized courses from YouTube, Coursera, or Udemy.
        
        Returns structured recommendations with title, platform, difficulty,
        duration, free/paid status, and links.
        """
        modalities_str = ", ".join(preferred_modalities) if preferred_modalities else "video, interactive"
        interests_str = f"\nSpecific interests: {interests}" if interests else ""
        
        prompt = f"""You are an expert learning advisor. Recommend exactly {num_recommendations} high-quality, REAL courses for learning "{skill}" at the {level.upper()} level.

=== LEARNER PROFILE ===
- Skill to learn: {skill}
- Current level: {level}
- Preferred learning styles: {modalities_str}{interests_str}

=== CONSTRAINTS ===
- ONLY recommend from: YouTube, Coursera, Udemy
- Recommend REAL, EXISTING courses that you know exist
- Match recommendations to the learner's {level} level
- Include a variety: some free, some paid
- Prioritize highly-rated, popular courses with good reviews
- Each recommendation should serve a different learning purpose

=== RECOMMENDATION VARIETY ===
For a {level} learner, include:
- Foundational courses to build core knowledge
- Practical/project-based courses for hands-on experience
- Quick tutorials for specific topics
- Comprehensive courses for deep learning

=== PLATFORM NOTES ===
- YouTube: Free tutorials. Include channel name. For playlists, note total videos.
- Coursera: University/company courses. Many offer "free audit" option.
- Udemy: Often $12-20 on sale. Include instructor name if well-known.

=== REQUIRED OUTPUT FORMAT ===
Respond ONLY with valid JSON array (no markdown, no explanation):
[
    {{
        "title": "<exact real course/video title>",
        "platform": "youtube" | "coursera" | "udemy",
        "url": "<actual URL - use real URLs you know>",
        "instructor": "<instructor or channel name>",
        "difficulty": "beginner" | "intermediate" | "advanced",
        "duration_hours": <estimated hours as number>,
        "is_free": <true if free, false if paid>,
        "price": "<Free, or price like '$49/month', '$19.99 on sale'>",
        "rating": <rating 1-5 as float, or null>,
        "why_recommended": "<personalized reason why this specific course helps a {level} learner of {skill}>"
    }}
]

IMPORTANT: Only recommend courses you are confident actually exist. Use real course names and instructors."""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            raise RuntimeError(f"Gemini recommendation failed: {e}")
    
    def interpret_quiz_answer(
        self,
        question: str,
        expected_concepts: List[str],
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Interpret free-form quiz answers for advanced quizzes.
        
        Returns scoring and feedback for open-ended questions.
        """
        concepts_str = ", ".join(expected_concepts)
        
        prompt = f"""You are grading a quiz response for a technical assessment.

=== QUESTION ===
{question}

=== EXPECTED CONCEPTS/KEYWORDS ===
{concepts_str}

=== STUDENT'S ANSWER ===
{user_answer}

=== GRADING CRITERIA ===
- Award points for each expected concept mentioned or demonstrated
- Consider partial credit for related concepts
- Evaluate technical accuracy
- Consider communication clarity

=== REQUIRED OUTPUT FORMAT ===
Respond ONLY with valid JSON:
{{
    "score_percentage": <0-100>,
    "concepts_demonstrated": ["<concept1>", "<concept2>"],
    "concepts_missing": ["<concept3>"],
    "feedback": "<constructive feedback for the learner>",
    "is_correct": <true if score >= 70, false otherwise>
}}"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            raise RuntimeError(f"Gemini answer interpretation failed: {e}")

    def generate_quiz_questions(
        self,
        skill: str,
        level: str,
        num_questions: int,
        topics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions dynamically using Gemini.
        
        Returns a list of question objects with prompt, options, and correct answer.
        """
        topics_str = f"\nFocus on these topics: {', '.join(topics)}" if topics else ""
        
        prompt = f"""You are an expert educator creating quiz questions for "{skill}" at the {level.upper()} level.

Generate exactly {num_questions} multiple-choice questions.{topics_str}

=== DIFFICULTY GUIDELINES ===
- BEGINNER: Basic terminology, simple concepts, recognition-level questions
- INTERMEDIATE: Application scenarios, code analysis, problem-solving
- ADVANCED: Complex scenarios, debugging, optimization, best practices

=== REQUIRED OUTPUT FORMAT ===
Respond ONLY with a valid JSON array:
[
    {{
        "question_id": "q1",
        "prompt": "<clear question text>",
        "options": [
            {{"value": "a", "label": "<option A text>"}},
            {{"value": "b", "label": "<option B text>"}},
            {{"value": "c", "label": "<option C text>"}},
            {{"value": "d", "label": "<option D text>"}}
        ],
        "correct_answer": "<a, b, c, or d>",
        "explanation": "<brief explanation of correct answer>",
        "difficulty": "{level}",
        "points": 1
    }}
]

=== REQUIREMENTS ===
- Each question must have exactly 4 options (a, b, c, d)
- Questions should be unique and test different concepts
- Avoid trick questions - test real understanding
- Make wrong answers plausible but clearly incorrect
- Include a mix of conceptual and practical questions
- IMPORTANT: Do NOT use backticks, code blocks, or special characters in questions/options
- Keep questions as plain text - describe code concepts in words, not code snippets
- Output ONLY the JSON array, no markdown formatting"""

        try:
            response = self.model.generate_content(prompt)
            questions = self._parse_json_response(response.text)
            
            if isinstance(questions, list):
                for i, q in enumerate(questions):
                    q["question_id"] = f"gen_{level}_{i+1}"
                    q["type"] = "multiple_choice"
                return questions
            return []
        except Exception as e:
            raise RuntimeError(f"Gemini quiz generation failed: {e}")
    
    def _format_responses(self, responses: Dict[str, Any]) -> str:
        """Format questionnaire responses for the prompt."""
        lines = []
        for key, value in responses.items():
            readable_key = key.replace("_", " ").replace("self rating", "Self-Rating:").title()
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"- {readable_key}: {value}")
        return "\n".join(lines)
    
    def _parse_json_response(self, text: str) -> Any:
        """Extract and parse JSON from Gemini response."""
        import re
        text = text.strip()
        
        # Remove markdown code blocks (```json ... ``` or ``` ... ```)
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        code_match = re.search(code_block_pattern, text)
        if code_match:
            text = code_match.group(1).strip()
        
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        start_markers = ['{', '[']
        end_markers = {'{': '}', '[': ']'}
        
        for start_marker in start_markers:
            start = text.find(start_marker)
            if start >= 0:
                end_marker = end_markers[start_marker]
                end = text.rfind(end_marker)
                if end > start:
                    json_str = text[start:end + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
        
        raise ValueError(f"Could not parse JSON from response: {text[:200]}")


class MockGeminiClient(GeminiClientBase):
    """
    Mock Gemini client for testing without API key.
    Returns deterministic responses based on input patterns.
    """
    
    def __init__(self, custom_responses: Optional[Dict[str, Any]] = None):
        """
        Initialize mock client with optional custom responses.
        
        Args:
            custom_responses: Dict mapping response types to mock data
        """
        self.custom_responses = custom_responses or {}
        self.call_log: List[Dict[str, Any]] = []
    
    def classify_skill_level(
        self,
        skill: str,
        questionnaire_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Mock classification based on self-ratings in responses.
        Uses deterministic logic to simulate Gemini's classification.
        """
        self.call_log.append({
            "method": "classify_skill_level",
            "skill": skill,
            "responses": questionnaire_responses
        })
        
        # Check for custom response
        if "classification" in self.custom_responses:
            return self.custom_responses["classification"]
        
        # Simulate Gemini classification based on self-ratings
        ratings = []
        for key, value in questionnaire_responses.items():
            if key.startswith("self_rating_") and value not in ["na", None]:
                try:
                    ratings.append(float(value))
                except (ValueError, TypeError):
                    pass
        
        # Get prior exposure weight
        exposure_weights = {
            "none": 0, "heard": 0.5, "tutorials": 1.5,
            "projects": 2.5, "professional": 3.5, "expert": 4.5
        }
        exposure = questionnaire_responses.get("prior_exposure", "none")
        exposure_score = exposure_weights.get(exposure, 1)
        
        # Calculate combined score (simulating Gemini's analysis)
        if ratings:
            mean_rating = sum(ratings) / len(ratings)
            combined = (mean_rating * 0.7) + (exposure_score * 0.3)
        else:
            combined = exposure_score
        
        # Determine level
        if combined < 2.5:
            level = "beginner"
            reasoning = [
                f"Low average self-rating ({mean_rating:.1f}/5)" if ratings else "No self-ratings provided",
                f"Limited prior exposure: {exposure}",
                "Recommend starting with foundational content"
            ]
        elif combined < 4.0:
            level = "intermediate"
            reasoning = [
                f"Moderate self-assessment ({mean_rating:.1f}/5)" if ratings else "Moderate prior exposure",
                f"Prior exposure indicates practical experience: {exposure}",
                "Ready for application-focused learning"
            ]
        else:
            level = "advanced"
            reasoning = [
                f"High self-assessment ({mean_rating:.1f}/5)" if ratings else "Strong prior exposure",
                f"Significant prior experience: {exposure}",
                "Ready for advanced topics and specialization"
            ]
        
        return {
            "level": level,
            "confidence": 0.85,
            "reasoning": reasoning
        }
    
    def get_course_recommendations(
        self,
        skill: str,
        level: str,
        preferred_modalities: List[str],
        interests: Optional[str] = None,
        num_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Return mock course recommendations based on skill and level.
        Recommendations are differentiated by skill level.
        """
        self.call_log.append({
            "method": "get_course_recommendations",
            "skill": skill,
            "level": level,
            "modalities": preferred_modalities
        })
        
        if "recommendations" in self.custom_responses:
            return self.custom_responses["recommendations"]
        
        import urllib.parse
        skill_encoded = urllib.parse.quote_plus(skill)
        skill_title = skill.title()
        
        # Use SEARCH URLs that are 100% GUARANTEED to work
        # These show search results, not specific videos/courses that might be deleted
        
        beginner_recommendations = [
            {
                "title": f"{skill_title} Beginner Tutorial - Full Course",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+beginner+tutorial+full+course",
                "instructor": "Various Creators",
                "difficulty": "beginner",
                "duration_hours": 4,
                "is_free": True,
                "price": "Free",
                "rating": 4.8,
                "why_recommended": f"Search results for best {skill} beginner tutorials - pick the most viewed one"
            },
            {
                "title": f"{skill_title} Crash Course for Beginners",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+crash+course+beginners+2024",
                "instructor": "Various Creators",
                "difficulty": "beginner",
                "duration_hours": 2,
                "is_free": True,
                "price": "Free",
                "rating": 4.7,
                "why_recommended": "Quick crash courses to get started fast - sorted by relevance"
            },
            {
                "title": f"{skill_title} for Beginners - Coursera",
                "platform": "coursera",
                "url": f"https://www.coursera.org/search?query={skill_encoded}&productDifficultyLevel=Beginner",
                "instructor": "Top Universities",
                "difficulty": "beginner",
                "duration_hours": 40,
                "is_free": False,
                "price": "Free to audit, $49/month for certificate",
                "rating": 4.7,
                "why_recommended": f"University-backed {skill} courses filtered for beginners"
            },
            {
                "title": f"{skill_title} Complete Bootcamp - Udemy",
                "platform": "udemy",
                "url": f"https://www.udemy.com/courses/search/?q={skill_encoded}&instructional_level=beginner&sort=relevance&ratings=4.0",
                "instructor": "Top Instructors",
                "difficulty": "beginner",
                "duration_hours": 30,
                "is_free": False,
                "price": "$14.99 (frequently on sale)",
                "rating": 4.6,
                "why_recommended": f"Highly-rated {skill} courses for beginners with lifetime access"
            },
            {
                "title": f"Learn {skill_title} Step by Step",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query=learn+{skill_encoded}+step+by+step+tutorial",
                "instructor": "Various Creators",
                "difficulty": "beginner",
                "duration_hours": 3,
                "is_free": True,
                "price": "Free",
                "rating": 4.8,
                "why_recommended": "Step-by-step tutorials perfect for absolute beginners"
            },
            {
                "title": f"{skill_title} Fundamentals Course",
                "platform": "coursera",
                "url": f"https://www.coursera.org/search?query={skill_encoded}+fundamentals",
                "instructor": "Industry Experts",
                "difficulty": "beginner",
                "duration_hours": 20,
                "is_free": False,
                "price": "Free to audit",
                "rating": 4.6,
                "why_recommended": f"Build strong {skill} foundations with structured learning"
            }
        ]
        
        intermediate_recommendations = [
            {
                "title": f"{skill_title} Projects Tutorial",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+project+tutorial+intermediate",
                "instructor": "Various Creators",
                "difficulty": "intermediate",
                "duration_hours": 5,
                "is_free": True,
                "price": "Free",
                "rating": 4.9,
                "why_recommended": f"Build real {skill} projects to solidify your skills"
            },
            {
                "title": f"Advanced {skill_title} Concepts",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+advanced+concepts+tutorial",
                "instructor": "Various Creators",
                "difficulty": "intermediate",
                "duration_hours": 4,
                "is_free": True,
                "price": "Free",
                "rating": 4.8,
                "why_recommended": "Deep dive into advanced concepts and techniques"
            },
            {
                "title": f"{skill_title} Professional Certificate",
                "platform": "coursera",
                "url": f"https://www.coursera.org/search?query={skill_encoded}&productDifficultyLevel=Intermediate&productTypeDescription=Professional%20Certificates",
                "instructor": "Google, IBM, Meta",
                "difficulty": "intermediate",
                "duration_hours": 80,
                "is_free": False,
                "price": "$49/month (7-day free trial)",
                "rating": 4.8,
                "why_recommended": "Industry-recognized professional certificates"
            },
            {
                "title": f"{skill_title} Real World Projects - Udemy",
                "platform": "udemy",
                "url": f"https://www.udemy.com/courses/search/?q={skill_encoded}+projects&instructional_level=intermediate&sort=relevance&ratings=4.0",
                "instructor": "Senior Developers",
                "difficulty": "intermediate",
                "duration_hours": 40,
                "is_free": False,
                "price": "$16.99 (frequently on sale)",
                "rating": 4.7,
                "why_recommended": f"Hands-on {skill} projects for real-world experience"
            },
            {
                "title": f"{skill_title} Best Practices",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+best+practices+tips",
                "instructor": "Various Creators",
                "difficulty": "intermediate",
                "duration_hours": 3,
                "is_free": True,
                "price": "Free",
                "rating": 4.7,
                "why_recommended": "Learn industry best practices and common patterns"
            },
            {
                "title": f"{skill_title} Intermediate Specialization",
                "platform": "coursera",
                "url": f"https://www.coursera.org/search?query={skill_encoded}&productDifficultyLevel=Intermediate",
                "instructor": "Top Universities",
                "difficulty": "intermediate",
                "duration_hours": 60,
                "is_free": False,
                "price": "Free to audit",
                "rating": 4.6,
                "why_recommended": "Comprehensive intermediate-level specializations"
            }
        ]
        
        advanced_recommendations = [
            {
                "title": f"{skill_title} System Design & Architecture",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+system+design+architecture",
                "instructor": "Various Creators",
                "difficulty": "advanced",
                "duration_hours": 8,
                "is_free": True,
                "price": "Free",
                "rating": 4.9,
                "why_recommended": "Learn to architect scalable systems"
            },
            {
                "title": f"{skill_title} Performance Optimization",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+performance+optimization+advanced",
                "instructor": "Various Creators",
                "difficulty": "advanced",
                "duration_hours": 6,
                "is_free": True,
                "price": "Free",
                "rating": 4.8,
                "why_recommended": "Advanced performance tuning and optimization techniques"
            },
            {
                "title": f"{skill_title} Advanced Specialization",
                "platform": "coursera",
                "url": f"https://www.coursera.org/search?query={skill_encoded}&productDifficultyLevel=Advanced&productTypeDescription=Specializations",
                "instructor": "Stanford, MIT, etc.",
                "difficulty": "advanced",
                "duration_hours": 60,
                "is_free": False,
                "price": "$49/month",
                "rating": 4.8,
                "why_recommended": "Advanced specializations from world-class universities"
            },
            {
                "title": f"{skill_title} Expert Masterclass - Udemy",
                "platform": "udemy",
                "url": f"https://www.udemy.com/courses/search/?q={skill_encoded}+advanced&instructional_level=expert&sort=relevance&ratings=4.5",
                "instructor": "Industry Experts",
                "difficulty": "advanced",
                "duration_hours": 50,
                "is_free": False,
                "price": "$19.99 (frequently on sale)",
                "rating": 4.7,
                "why_recommended": f"Expert-level {skill} courses for production-ready skills"
            },
            {
                "title": f"{skill_title} Interview Preparation",
                "platform": "youtube",
                "url": f"https://www.youtube.com/results?search_query={skill_encoded}+interview+questions+senior",
                "instructor": "Various Creators",
                "difficulty": "advanced",
                "duration_hours": 4,
                "is_free": True,
                "price": "Free",
                "rating": 4.8,
                "why_recommended": "Prepare for senior-level technical interviews"
            },
            {
                "title": f"{skill_title} Production Best Practices",
                "platform": "coursera",
                "url": f"https://www.coursera.org/search?query={skill_encoded}+production+enterprise",
                "instructor": "Tech Companies",
                "difficulty": "advanced",
                "duration_hours": 40,
                "is_free": False,
                "price": "Free to audit",
                "rating": 4.6,
                "why_recommended": "Enterprise-grade practices for production environments"
            }
        ]
        
        # Select recommendations based on level
        if level == "beginner":
            recommendations = beginner_recommendations
        elif level == "intermediate":
            recommendations = intermediate_recommendations
        else:  # advanced
            recommendations = advanced_recommendations
        
        return recommendations[:num_recommendations]
    
    def interpret_quiz_answer(
        self,
        question: str,
        expected_concepts: List[str],
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Mock interpretation of free-form answers.
        """
        self.call_log.append({
            "method": "interpret_quiz_answer",
            "question": question,
            "expected_concepts": expected_concepts,
            "user_answer": user_answer
        })
        
        # Check for custom response
        if "quiz_interpretation" in self.custom_responses:
            return self.custom_responses["quiz_interpretation"]
        
        # Simple mock scoring based on answer length and concept mentions
        answer_lower = user_answer.lower()
        found_concepts = [c for c in expected_concepts if c.lower() in answer_lower]
        missing_concepts = [c for c in expected_concepts if c.lower() not in answer_lower]
        
        score = (len(found_concepts) / len(expected_concepts)) * 100 if expected_concepts else 50
        
        # Bonus for detailed answers
        if len(user_answer) > 200:
            score = min(100, score + 10)
        
        return {
            "score_percentage": round(score),
            "concepts_demonstrated": found_concepts,
            "concepts_missing": missing_concepts,
            "feedback": f"You covered {len(found_concepts)} of {len(expected_concepts)} expected concepts.",
            "is_correct": score >= 70
        }

    def generate_quiz_questions(
        self,
        skill: str,
        level: str,
        num_questions: int,
        topics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate mock quiz questions for testing.
        Returns deterministic questions based on skill and level.
        """
        self.call_log.append({
            "method": "generate_quiz_questions",
            "skill": skill,
            "level": level,
            "num_questions": num_questions
        })
        
        if "quiz_questions" in self.custom_responses:
            return self.custom_responses["quiz_questions"]
        
        skill_title = skill.title()
        
        # Generate skill-agnostic questions that work for ANY skill
        question_templates = {
            "beginner": [
                {
                    "prompt": f"What is the primary purpose of {skill_title}?",
                    "options": [
                        {"value": "a", "label": f"To build user interfaces and interactive applications"},
                        {"value": "b", "label": f"To manage databases and storage systems"},
                        {"value": "c", "label": f"To handle network security protocols"},
                        {"value": "d", "label": f"To compile machine code directly"}
                    ],
                    "correct_answer": "a",
                    "explanation": f"{skill_title} is primarily used for building applications and solving specific domain problems."
                },
                {
                    "prompt": f"Which of the following is a key benefit of learning {skill_title}?",
                    "options": [
                        {"value": "a", "label": "It has no practical applications"},
                        {"value": "b", "label": "It is widely used in the industry with strong job demand"},
                        {"value": "c", "label": "It can only be used offline"},
                        {"value": "d", "label": "It requires no practice to master"}
                    ],
                    "correct_answer": "b",
                    "explanation": f"{skill_title} has strong industry demand and practical applications."
                },
                {
                    "prompt": f"What is typically the first step when starting to learn {skill_title}?",
                    "options": [
                        {"value": "a", "label": "Build a complex production application immediately"},
                        {"value": "b", "label": "Learn the fundamental concepts and basic syntax/principles"},
                        {"value": "c", "label": "Skip documentation and dive into advanced topics"},
                        {"value": "d", "label": "Memorize everything without practicing"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Starting with fundamentals builds a strong foundation for advanced learning."
                },
                {
                    "prompt": f"Which learning approach is most effective for mastering {skill_title}?",
                    "options": [
                        {"value": "a", "label": "Only reading without any hands-on practice"},
                        {"value": "b", "label": "Combining theory with practical projects and exercises"},
                        {"value": "c", "label": "Watching videos without taking notes"},
                        {"value": "d", "label": "Skipping beginner content entirely"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Hands-on practice combined with theory is the most effective learning approach."
                },
                {
                    "prompt": f"What resource is most helpful when stuck on a {skill_title} problem?",
                    "options": [
                        {"value": "a", "label": "Official documentation and community forums"},
                        {"value": "b", "label": "Ignoring the problem and moving on"},
                        {"value": "c", "label": "Giving up on learning"},
                        {"value": "d", "label": "Randomly changing things until it works"}
                    ],
                    "correct_answer": "a",
                    "explanation": "Documentation and community resources are invaluable for problem-solving."
                },
                {
                    "prompt": f"Why is consistent practice important when learning {skill_title}?",
                    "options": [
                        {"value": "a", "label": "It isn't - you can learn everything in one day"},
                        {"value": "b", "label": "It builds muscle memory and deepens understanding"},
                        {"value": "c", "label": "Practice is only for beginners"},
                        {"value": "d", "label": "Experts never practice"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Consistent practice reinforces learning and builds lasting skills."
                }
            ],
            "intermediate": [
                {
                    "prompt": f"What distinguishes an intermediate {skill_title} practitioner from a beginner?",
                    "options": [
                        {"value": "a", "label": "They can only follow tutorials"},
                        {"value": "b", "label": "They can solve problems independently and understand underlying concepts"},
                        {"value": "c", "label": "They have memorized all documentation"},
                        {"value": "d", "label": "They never make mistakes"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Intermediate practitioners can work independently and understand why things work."
                },
                {
                    "prompt": f"When working on a complex {skill_title} project, what approach is best?",
                    "options": [
                        {"value": "a", "label": "Write all code at once without testing"},
                        {"value": "b", "label": "Break it into smaller, manageable components"},
                        {"value": "c", "label": "Copy everything from the internet"},
                        {"value": "d", "label": "Avoid planning and start coding immediately"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Breaking problems into smaller parts makes complex projects manageable."
                },
                {
                    "prompt": f"How should you handle errors and bugs in {skill_title}?",
                    "options": [
                        {"value": "a", "label": "Ignore them and hope they go away"},
                        {"value": "b", "label": "Read error messages, debug systematically, and learn from mistakes"},
                        {"value": "c", "label": "Delete everything and start over"},
                        {"value": "d", "label": "Blame the tools"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Systematic debugging and learning from errors is crucial for improvement."
                },
                {
                    "prompt": f"What is the importance of code/work organization in {skill_title}?",
                    "options": [
                        {"value": "a", "label": "Organization doesn't matter"},
                        {"value": "b", "label": "Good organization improves maintainability and collaboration"},
                        {"value": "c", "label": "Messy work is faster"},
                        {"value": "d", "label": "Only beginners need organization"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Well-organized work is easier to maintain, debug, and share with others."
                },
                {
                    "prompt": f"How can you continue improving your {skill_title} skills at the intermediate level?",
                    "options": [
                        {"value": "a", "label": "Stop learning - intermediate is enough"},
                        {"value": "b", "label": "Build real projects, contribute to open source, and learn from experts"},
                        {"value": "c", "label": "Only repeat beginner tutorials"},
                        {"value": "d", "label": "Avoid challenging yourself"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Real projects and community involvement accelerate skill development."
                }
            ],
            "advanced": [
                {
                    "prompt": f"What characterizes an advanced {skill_title} practitioner?",
                    "options": [
                        {"value": "a", "label": "They know everything and never need to learn"},
                        {"value": "b", "label": "They understand deep principles, can architect solutions, and mentor others"},
                        {"value": "c", "label": "They work alone and never collaborate"},
                        {"value": "d", "label": "They only use basic features"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Advanced practitioners have deep understanding and can guide others."
                },
                {
                    "prompt": f"When designing a solution using {skill_title}, what should be prioritized?",
                    "options": [
                        {"value": "a", "label": "Getting it done as fast as possible regardless of quality"},
                        {"value": "b", "label": "Scalability, maintainability, and best practices"},
                        {"value": "c", "label": "Using as many features as possible"},
                        {"value": "d", "label": "Making it as complex as possible"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Quality solutions prioritize scalability and long-term maintainability."
                },
                {
                    "prompt": f"How do experts stay current with {skill_title} developments?",
                    "options": [
                        {"value": "a", "label": "They don't - their knowledge is complete"},
                        {"value": "b", "label": "Following industry news, contributing to community, and continuous learning"},
                        {"value": "c", "label": "Ignoring all new developments"},
                        {"value": "d", "label": "Only reading outdated materials"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Continuous learning and community involvement keep experts current."
                },
                {
                    "prompt": f"What is the best way to share {skill_title} knowledge with others?",
                    "options": [
                        {"value": "a", "label": "Keep knowledge secret"},
                        {"value": "b", "label": "Write documentation, mentor juniors, and create educational content"},
                        {"value": "c", "label": "Only help people who pay"},
                        {"value": "d", "label": "Avoid teaching entirely"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Sharing knowledge through documentation and mentoring benefits the entire community."
                },
                {
                    "prompt": f"When facing a novel problem in {skill_title}, what approach works best?",
                    "options": [
                        {"value": "a", "label": "Give up if there's no existing solution"},
                        {"value": "b", "label": "Research, experiment, and apply first principles thinking"},
                        {"value": "c", "label": "Wait for someone else to solve it"},
                        {"value": "d", "label": "Use only familiar approaches even if inappropriate"}
                    ],
                    "correct_answer": "b",
                    "explanation": "Novel problems require research, experimentation, and creative thinking."
                }
            ]
        }
        
        import random
        templates = question_templates.get(level, question_templates["beginner"])
        selected = random.sample(templates, min(num_questions, len(templates)))
        
        questions = []
        for i, template in enumerate(selected):
            questions.append({
                "question_id": f"gen_{level}_{i+1}",
                "type": "multiple_choice",
                "prompt": template["prompt"],
                "options": template["options"],
                "correct_answer": template["correct_answer"],
                "explanation": template["explanation"],
                "difficulty": level,
                "points": 1
            })
        
        return questions


def get_gemini_client(use_mock: bool = False) -> GeminiClientBase:
    """
    Factory function to get appropriate Gemini client.
    
    Args:
        use_mock: Force mock client even if API key is available
    
    Returns:
        GeminiClient if API key configured and not mocking,
        MockGeminiClient otherwise
    """
    if use_mock:
        return MockGeminiClient()
    
    if GEMINI_AVAILABLE and settings.gemini_api_key:
        try:
            return GeminiClient()
        except Exception as e:
            print(f"Warning: Could not initialize Gemini client: {e}")
            print("Falling back to mock client")
            return MockGeminiClient()
    
    return MockGeminiClient()


# Global client instance - initialized on first use
_gemini_client: Optional[GeminiClientBase] = None


def get_client() -> GeminiClientBase:
    """Get the global Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = get_gemini_client()
    return _gemini_client


def set_client(client: GeminiClientBase):
    """Set a custom client (useful for testing)."""
    global _gemini_client
    _gemini_client = client
