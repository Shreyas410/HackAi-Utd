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
        Ask Gemini to recommend courses with DIRECT URLs when possible.
        
        Gemini should return actual course/video URLs, not search URLs.
        If Gemini is unsure about a URL, it should omit it rather than hallucinate.
        """
        modalities_str = ", ".join(preferred_modalities) if preferred_modalities else "video"
        interests_str = f"\nSpecific interests: {interests}" if interests else ""
        
        prompt = f"""You are an expert learning advisor. Recommend exactly {num_recommendations} REAL courses for "{skill}" at the {level.upper()} level.

=== LEARNER PROFILE ===
- Skill: {skill}
- Level: {level}
- Preferred formats: {modalities_str}{interests_str}

=== CRITICAL REQUIREMENTS ===
1. ONLY platform: youtube (no Coursera, no Udemy)
2. Prefer REAL, EXISTING videos you are confident about
3. If you know the actual URL, include it
4. If you are NOT confident about a URL, OMIT the url field entirely
5. NEVER hallucinate or make up fake URLs
6. Include query field as backup for finding the resource

=== OUTPUT FORMAT ===
Return ONLY valid JSON array. NO markdown. NO explanation.

Each item MUST have:
- "title": exact or close video/course title
- "platform": "youtube" (only YouTube)
- "description": brief description
- "reason": why good for {level} learner
- "difficulty": "{level}"
- "query": search terms to find this (always include)

Each item SHOULD have (if you are confident):
- "url": DIRECT URL to the video (NOT a search URL)

=== URL GUIDELINES ===
YouTube: https://www.youtube.com/watch?v=VIDEO_ID

DO NOT return search result URLs like:
- youtube.com/results?search_query=

=== EXAMPLE OUTPUT ===
[
  {{
    "title": "Node.js Tutorial for Beginners",
    "platform": "youtube",
    "url": "https://www.youtube.com/watch?v=TlB_eWDSMt4",
    "query": "nodejs tutorial beginners mosh",
    "description": "1-hour intro to Node.js fundamentals",
    "reason": "Popular beginner-friendly Node tutorial",
    "difficulty": "beginner"
  }},
  {{
    "title": "Python for Everybody - Full Course",
    "platform": "youtube",
    "query": "python for everybody freecodecamp",
    "description": "Complete Python course",
    "reason": "Comprehensive Python for beginners",
    "difficulty": "beginner"
  }}
]

Return {num_recommendations} recommendations as JSON:"""

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            print(f"[Gemini] Raw recommendation response length: {len(raw_text)}")
            
            result = self._parse_gemini_recommendations(raw_text)
            return result
            
        except Exception as e:
            print(f"[Gemini] Recommendation failed: {e}")
            return []
    
    def _parse_gemini_recommendations(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Parse and validate Gemini recommendation response.
        Handles malformed JSON, code fences, and validates URLs.
        """
        try:
            parsed = self._parse_json_response(raw_text)
            
            if not isinstance(parsed, list):
                print(f"[Gemini] Expected list, got {type(parsed)}")
                return []
            
            valid_recommendations = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                
                platform = item.get("platform", "").lower()
                if platform != "youtube":
                    print(f"[Gemini] Rejected non-YouTube platform: {platform}")
                    continue
                
                title = item.get("title", "")
                query = item.get("query", "")
                url = item.get("url", "")
                
                if not title and not query:
                    print(f"[Gemini] Rejected: missing both title and query")
                    continue
                
                # Validate URL if provided - reject search URLs
                if url:
                    url_lower = url.lower()
                    is_search_url = any(p in url_lower for p in [
                        "/results?search_query=",
                        "/search?",
                        "/courses/search/"
                    ])
                    if is_search_url:
                        print(f"[Gemini] Rejecting search URL: {url[:50]}")
                        url = ""  # Clear invalid search URL
                
                valid_recommendations.append({
                    "title": title or f"Recommended {platform.title()} Resource",
                    "platform": platform,
                    "query": query,
                    "url": url,
                    "description": item.get("description", ""),
                    "reason": item.get("reason", item.get("why_recommended", "")),
                    "difficulty": item.get("difficulty", "intermediate").lower(),
                    "is_free": item.get("is_free", platform == "youtube"),
                    "duration_hours": item.get("duration_hours"),
                    "rating": item.get("rating"),
                    "source": "gemini"
                })
            
            print(f"[Gemini] Parsed {len(valid_recommendations)} valid recommendations")
            return valid_recommendations
            
        except Exception as e:
            print(f"[Gemini] Parse error: {e}")
            return []
    
    def generate_youtube_search_queries(
        self,
        skill: str,
        level: str,
        num_queries: int = 3
    ) -> List[str]:
        """
        Generate optimized YouTube search queries for a skill and level.
        
        Instead of asking Gemini for video URLs (which it hallucinates),
        we ask it to generate optimal search queries that we'll use
        with the YouTube Data API.
        
        Returns a list of search query strings.
        """
        prompt = f"""You are a YouTube search expert. Generate {num_queries} optimal search queries to find the best educational videos for learning "{skill}" at the {level.upper()} level.

=== REQUIREMENTS ===
- Each query should find DIFFERENT types of content (tutorial, course, crash course, project-based, etc.)
- Queries should be specific enough to find relevant videos
- Include level-appropriate terms (beginner/intermediate/advanced)
- Use keywords that popular educational channels use

=== OUTPUT FORMAT ===
Return ONLY a JSON array of strings. No markdown, no explanation:
["query 1", "query 2", "query 3"]

=== EXAMPLES ===
For "Python" at "beginner" level:
["python tutorial for beginners complete course", "learn python programming basics 2024", "python crash course absolute beginners"]

For "React" at "intermediate" level:
["react hooks tutorial projects", "react advanced patterns best practices", "build react app intermediate tutorial"]

Generate {num_queries} queries for "{skill}" at "{level}" level:"""

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            # Parse the JSON array
            queries = self._parse_json_response(raw_text)
            
            if isinstance(queries, list):
                # Filter to only string queries
                valid_queries = [q for q in queries if isinstance(q, str) and len(q) > 5]
                if valid_queries:
                    print(f"[Gemini] Generated {len(valid_queries)} YouTube search queries")
                    return valid_queries[:num_queries]
            
            print(f"[Gemini] Failed to parse search queries, using fallback")
            return []
            
        except Exception as e:
            print(f"[Gemini] Search query generation failed: {e}")
            return []
    
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
        
        if not text:
            raise ValueError("Empty response from Gemini")
        
        text = text.strip()
        
        # Remove markdown code blocks (```json ... ``` or ``` ... ```)
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        code_match = re.search(code_block_pattern, text)
        if code_match:
            text = code_match.group(1).strip()
        
        # Clean up common issues
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find and extract JSON array or object
        start_markers = ['[', '{']
        end_markers = {'[': ']', '{': '}'}
        
        for start_marker in start_markers:
            start = text.find(start_marker)
            if start >= 0:
                end_marker = end_markers[start_marker]
                # Find matching bracket by counting
                depth = 0
                in_string = False
                escape_next = False
                end_pos = -1
                
                for i, char in enumerate(text[start:], start):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if char == start_marker:
                        depth += 1
                    elif char == end_marker:
                        depth -= 1
                        if depth == 0:
                            end_pos = i
                            break
                
                if end_pos > start:
                    json_str = text[start:end_pos + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        print(f"[Gemini] JSON parse attempt failed: {e}")
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
        Return mock course recommendations with DIRECT URLs when available.
        Simulates real Gemini behavior - sometimes has URLs, sometimes only queries.
        """
        self.call_log.append({
            "method": "get_course_recommendations",
            "skill": skill,
            "level": level,
            "modalities": preferred_modalities
        })
        
        if "recommendations" in self.custom_responses:
            return self.custom_responses["recommendations"]
        
        skill_title = skill.title()
        skill_lower = skill.lower()
        
        # Mock recommendations with some direct URLs, some without
        # This simulates realistic Gemini behavior
        beginner_recommendations = [
            {
                "title": f"{skill_title} Tutorial for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=PkZNo7MFNFg",  # Real URL example
                "query": f"{skill_lower} tutorial beginner complete",
                "description": f"Comprehensive beginner tutorial for {skill}",
                "reason": f"Perfect starting point for learning {skill}",
                "difficulty": "beginner",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Crash Course",
                "platform": "youtube",
                "query": f"{skill_lower} crash course basics",
                "description": f"Quick introduction to {skill} essentials",
                "reason": "Fast-paced overview to get started quickly",
                "difficulty": "beginner",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Specialization",
                "platform": "coursera",
                "url": "https://www.coursera.org/specializations/python",  # Example
                "query": f"{skill_lower} specialization beginner",
                "description": f"University-backed {skill} course",
                "reason": "Structured curriculum with certification",
                "difficulty": "beginner",
                "is_free": False,
                "source": "gemini"
            },
            {
                "title": f"Complete {skill_title} Bootcamp",
                "platform": "udemy",
                "query": f"{skill_lower} bootcamp complete beginner",
                "description": f"Comprehensive {skill} bootcamp",
                "reason": "Hands-on learning with projects",
                "difficulty": "beginner",
                "is_free": False,
                "source": "gemini"
            },
            {
                "title": f"Learn {skill_title} - Full Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
                "query": f"learn {skill_lower} full course",
                "description": f"Complete {skill} course",
                "reason": "Comprehensive free tutorial",
                "difficulty": "beginner",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Fundamentals",
                "platform": "coursera",
                "query": f"{skill_lower} fundamentals introduction",
                "description": f"Core {skill} concepts",
                "reason": "Solid foundation building",
                "difficulty": "beginner",
                "is_free": False,
                "source": "gemini"
            }
        ]
        
        intermediate_recommendations = [
            {
                "title": f"{skill_title} Projects Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=Oe421EPjeBE",
                "query": f"{skill_lower} projects tutorial",
                "description": f"Build real {skill} projects",
                "reason": "Learn by building applications",
                "difficulty": "intermediate",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"Advanced {skill_title} Concepts",
                "platform": "youtube",
                "query": f"{skill_lower} advanced concepts",
                "description": f"Deep dive into {skill}",
                "reason": "Master advanced patterns",
                "difficulty": "intermediate",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Professional Certificate",
                "platform": "coursera",
                "url": "https://www.coursera.org/professional-certificates/google-it-support",
                "query": f"{skill_lower} professional certificate",
                "description": f"Industry certification for {skill}",
                "reason": "Career advancement credential",
                "difficulty": "intermediate",
                "is_free": False,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Complete Guide",
                "platform": "udemy",
                "url": "https://www.udemy.com/course/the-complete-javascript-course/",
                "query": f"{skill_lower} complete guide",
                "description": f"In-depth {skill} course",
                "reason": "Comprehensive training",
                "difficulty": "intermediate",
                "is_free": False,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Best Practices",
                "platform": "youtube",
                "query": f"{skill_lower} best practices",
                "description": f"Professional {skill} techniques",
                "reason": "Industry best practices",
                "difficulty": "intermediate",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Deep Dive",
                "platform": "coursera",
                "query": f"{skill_lower} in depth intermediate",
                "description": f"Thorough {skill} coverage",
                "reason": "Comprehensive understanding",
                "difficulty": "intermediate",
                "is_free": False,
                "source": "gemini"
            }
        ]
        
        advanced_recommendations = [
            {
                "title": f"{skill_title} System Design",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=bUHFg8CZFws",
                "query": f"{skill_lower} system design architecture",
                "description": f"Enterprise {skill} architecture",
                "reason": "Scale applications properly",
                "difficulty": "advanced",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Performance Optimization",
                "platform": "youtube",
                "query": f"{skill_lower} performance optimization",
                "description": f"Optimize {skill} applications",
                "reason": "Performance tuning mastery",
                "difficulty": "advanced",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"Advanced {skill_title} Specialization",
                "platform": "coursera",
                "url": "https://www.coursera.org/specializations/deep-learning",
                "query": f"{skill_lower} advanced specialization",
                "description": f"Expert {skill} training",
                "reason": "Advanced certification",
                "difficulty": "advanced",
                "is_free": False,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Expert Masterclass",
                "platform": "udemy",
                "query": f"{skill_lower} masterclass expert",
                "description": f"Production-grade {skill}",
                "reason": "Industry veteran insights",
                "difficulty": "advanced",
                "is_free": False,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Interview Prep",
                "platform": "youtube",
                "query": f"{skill_lower} interview preparation senior questions",
                "description": f"Ace {skill} technical interviews",
                "reason": "Prepare for senior-level interviews",
                "difficulty": "advanced",
                "is_free": True,
                "source": "gemini"
            },
            {
                "title": f"{skill_title} Production Best Practices",
                "platform": "coursera",
                "query": f"{skill_lower} production enterprise best practices",
                "description": f"Enterprise-grade {skill} practices",
                "reason": "Learn production-ready techniques",
                "difficulty": "advanced",
                "is_free": False,
                "source": "gemini"
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
    
    def generate_youtube_search_queries(
        self,
        skill: str,
        level: str,
        num_queries: int = 3
    ) -> List[str]:
        """
        Generate mock YouTube search queries for testing.
        """
        self.call_log.append({
            "method": "generate_youtube_search_queries",
            "skill": skill,
            "level": level,
            "num_queries": num_queries
        })
        
        if "youtube_queries" in self.custom_responses:
            return self.custom_responses["youtube_queries"]
        
        skill_lower = skill.lower()
        level_lower = level.lower()
        
        # Generate realistic search queries
        queries = [
            f"{skill_lower} tutorial for {level_lower}s complete course",
            f"learn {skill_lower} {level_lower} programming",
            f"{skill_lower} crash course {level_lower}"
        ]
        
        return queries[:num_queries]
    
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
