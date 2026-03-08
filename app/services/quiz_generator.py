"""
Diagnostic quiz generation service.
Generates level-appropriate quizzes based on skill configuration.
Uses Gemini to interpret free-form answers for advanced quizzes.
"""

import json
import os
import random
import uuid
from typing import List, Dict, Any, Optional, Tuple
from ..models.schemas import (
    SkillLevel, QuizQuestion, QuestionOption, QuestionType,
    QuizResult, QuizAnswer
)
from ..config import SKILLS_CONFIG_DIR, settings
from .gemini_client import get_client


class QuizGeneratorService:
    """
    Service for generating and scoring diagnostic quizzes.
    
    Quiz difficulty is tailored to learner level:
    - Beginner: Basic terminology and recognition
    - Intermediate: Scenario-based multiple choice requiring application
    - Advanced: Open-ended or multi-step problem solving (scored by Gemini)
    """
    
    def __init__(self):
        self._skill_configs: Dict[str, Any] = {}
    
    def _normalize_skill_name(self, skill: str) -> str:
        """Convert skill name to config file name."""
        return skill.lower().replace(" ", "_").replace("-", "_")
    
    def _load_skill_config(self, skill: str) -> Optional[Dict[str, Any]]:
        """Load skill configuration from JSON file."""
        normalized = self._normalize_skill_name(skill)
        
        if normalized in self._skill_configs:
            return self._skill_configs[normalized]
        
        config_path = os.path.join(SKILLS_CONFIG_DIR, f"{normalized}.json")
        
        if not os.path.exists(config_path):
            if os.path.exists(SKILLS_CONFIG_DIR):
                for filename in os.listdir(SKILLS_CONFIG_DIR):
                    if normalized in filename or filename.replace(".json", "") in normalized:
                        config_path = os.path.join(SKILLS_CONFIG_DIR, filename)
                        break
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._skill_configs[normalized] = config
                return config
        
        return None
    
    def generate_quiz(
        self,
        skill: str,
        level: SkillLevel,
        num_questions: Optional[int] = None
    ) -> Tuple[str, List[QuizQuestion], int]:
        """
        Generate a diagnostic quiz for the given skill and level.
        
        Args:
            skill: The skill being assessed
            level: Target difficulty level
            num_questions: Number of questions (default: 5-10 based on config)
        
        Returns:
            Tuple of (quiz_id, questions, total_points)
        """
        skill_config = self._load_skill_config(skill)
        
        if num_questions is None:
            num_questions = random.randint(
                settings.min_quiz_questions,
                settings.max_quiz_questions
            )
        
        quiz_id = str(uuid.uuid4())
        questions: List[QuizQuestion] = []
        
        # Try to generate questions using Gemini first
        try:
            questions = self._generate_with_gemini(skill, level, num_questions)
        except Exception as e:
            print(f"Gemini quiz generation failed: {e}, falling back to config")
            questions = []
        
        # Fall back to config-based questions if Gemini fails or returns empty
        if not questions:
            if skill_config and "quiz_questions" in skill_config:
                questions = self._generate_from_config(skill_config, level, num_questions)
            else:
                questions = self._generate_generic_quiz(skill, level, num_questions)
        
        total_points = sum(q.points for q in questions)
        
        return quiz_id, questions, total_points
    
    def _generate_with_gemini(
        self,
        skill: str,
        level: SkillLevel,
        num_questions: int
    ) -> List[QuizQuestion]:
        """Generate quiz questions dynamically using Gemini AI."""
        client = get_client()
        
        gemini_questions = client.generate_quiz_questions(
            skill=skill,
            level=level.value,
            num_questions=num_questions
        )
        
        questions = []
        for q_data in gemini_questions:
            options = [
                QuestionOption(value=opt["value"], label=opt["label"])
                for opt in q_data.get("options", [])
            ]
            
            questions.append(QuizQuestion(
                question_id=q_data.get("question_id", f"gen_{len(questions)}"),
                type=QuestionType.MULTIPLE_CHOICE,
                prompt=q_data.get("prompt", ""),
                options=options,
                difficulty=level,
                points=q_data.get("points", 1),
                time_limit_seconds=q_data.get("time_limit"),
                correct_answer=q_data.get("correct_answer"),
                explanation=q_data.get("explanation")
            ))
        
        return questions
    
    def _generate_from_config(
        self,
        config: Dict[str, Any],
        level: SkillLevel,
        num_questions: int
    ) -> List[QuizQuestion]:
        """Generate quiz questions from skill configuration."""
        quiz_bank = config.get("quiz_questions", {})
        level_questions = quiz_bank.get(level.value, [])
        
        # If not enough questions at target level, mix in adjacent levels
        if len(level_questions) < num_questions:
            if level == SkillLevel.INTERMEDIATE:
                level_questions.extend(quiz_bank.get("beginner", []))
                level_questions.extend(quiz_bank.get("advanced", []))
            elif level == SkillLevel.BEGINNER:
                level_questions.extend(quiz_bank.get("intermediate", []))
            else:
                level_questions.extend(quiz_bank.get("intermediate", []))
        
        # Sample questions
        selected = random.sample(
            level_questions,
            min(num_questions, len(level_questions))
        )
        
        questions = []
        for q_data in selected:
            question_type = QuestionType(q_data.get("type", "multiple_choice"))
            
            options = None
            if "options" in q_data:
                options = [
                    QuestionOption(value=opt["value"], label=opt["label"])
                    for opt in q_data["options"]
                ]
            
            questions.append(QuizQuestion(
                question_id=q_data["question_id"],
                type=question_type,
                prompt=q_data["prompt"],
                options=options,
                difficulty=level,
                points=q_data.get("points", 1),
                time_limit_seconds=q_data.get("time_limit")
            ))
        
        return questions
    
    def _generate_generic_quiz(
        self,
        skill: str,
        level: SkillLevel,
        num_questions: int
    ) -> List[QuizQuestion]:
        """Generate generic quiz questions when no config exists."""
        questions = []
        
        if level == SkillLevel.BEGINNER:
            quiz_data = [
                {
                    "prompt": f"What is the primary purpose of {skill}?",
                    "options": [
                        ("a", f"Building applications and solving problems in its domain"),
                        ("b", "Managing hardware resources directly"),
                        ("c", "Only for database administration"),
                        ("d", "Exclusively for system security")
                    ],
                    "correct": "a"
                },
                {
                    "prompt": f"Which of the following best describes {skill}?",
                    "options": [
                        ("a", "An outdated technology no longer in use"),
                        ("b", f"A tool/technology widely used in modern development"),
                        ("c", "Only useful for academic purposes"),
                        ("d", "A hardware specification standard")
                    ],
                    "correct": "b"
                },
                {
                    "prompt": f"What is a common use case for {skill}?",
                    "options": [
                        ("a", f"Building real-world applications and projects"),
                        ("b", "Only theoretical calculations"),
                        ("c", "Manufacturing physical devices"),
                        ("d", "None - it has no practical applications")
                    ],
                    "correct": "a"
                },
                {
                    "prompt": f"When learning {skill}, what should you focus on first?",
                    "options": [
                        ("a", "Advanced optimization techniques"),
                        ("b", f"Understanding the basic concepts and fundamentals"),
                        ("c", "Memorizing all syntax without practice"),
                        ("d", "Skipping documentation entirely")
                    ],
                    "correct": "b"
                },
                {
                    "prompt": f"Why is {skill} valuable to learn?",
                    "options": [
                        ("a", "It has no job market demand"),
                        ("b", "It can only be used offline"),
                        ("c", f"It is widely used with strong industry demand"),
                        ("d", "It requires no practice to master")
                    ],
                    "correct": "c"
                }
            ]
            for i, q in enumerate(quiz_data[:num_questions]):
                questions.append(QuizQuestion(
                    question_id=f"generic_b_{i}",
                    type=QuestionType.MULTIPLE_CHOICE,
                    prompt=q["prompt"],
                    options=[QuestionOption(value=v, label=l) for v, l in q["options"]],
                    correct_answer=q["correct"],
                    difficulty=level,
                    points=1
                ))
        
        elif level == SkillLevel.INTERMEDIATE:
            quiz_data = [
                {
                    "prompt": f"When debugging an issue in {skill}, what is the best first step?",
                    "options": [
                        ("a", "Rewrite the entire codebase"),
                        ("b", f"Identify and isolate the problem area systematically"),
                        ("c", "Ignore the error and hope it goes away"),
                        ("d", "Delete all related files")
                    ],
                    "correct": "b"
                },
                {
                    "prompt": f"What makes code in {skill} maintainable?",
                    "options": [
                        ("a", "Writing everything in one large file"),
                        ("b", "Using cryptic variable names"),
                        ("c", f"Following best practices, clear naming, and modular design"),
                        ("d", "Avoiding all comments and documentation")
                    ],
                    "correct": "c"
                },
                {
                    "prompt": f"How do you handle errors effectively in {skill}?",
                    "options": [
                        ("a", "Ignore all errors"),
                        ("b", f"Use proper error handling and provide meaningful feedback"),
                        ("c", "Let the application crash without handling"),
                        ("d", "Hide errors from users without logging")
                    ],
                    "correct": "b"
                },
                {
                    "prompt": f"What is important when scaling a {skill} application?",
                    "options": [
                        ("a", f"Performance optimization and efficient resource usage"),
                        ("b", "Using the oldest available version"),
                        ("c", "Avoiding all testing"),
                        ("d", "Hardcoding all configuration values")
                    ],
                    "correct": "a"
                },
                {
                    "prompt": f"Which practice improves {skill} project quality?",
                    "options": [
                        ("a", "Skipping code reviews"),
                        ("b", "Never writing tests"),
                        ("c", f"Writing tests and following coding standards"),
                        ("d", "Deploying without any verification")
                    ],
                    "correct": "c"
                }
            ]
            for i, q in enumerate(quiz_data[:num_questions]):
                questions.append(QuizQuestion(
                    question_id=f"generic_i_{i}",
                    type=QuestionType.MULTIPLE_CHOICE,
                    prompt=q["prompt"],
                    options=[QuestionOption(value=v, label=l) for v, l in q["options"]],
                    correct_answer=q["correct"],
                    difficulty=level,
                    points=2
                ))
        
        else:  # Advanced
            templates = [
                f"Explain your approach to optimizing a complex {skill} implementation.",
                f"How would you architect a large-scale solution using {skill}?",
                f"Describe best practices for {skill} in a production environment.",
                f"What are the key considerations when scaling {skill}?",
                f"How would you mentor someone learning {skill}?"
            ]
            for i, prompt in enumerate(templates[:num_questions]):
                questions.append(QuizQuestion(
                    question_id=f"generic_a_{i}",
                    type=QuestionType.TEXT,
                    prompt=prompt,
                    options=None,
                    difficulty=level,
                    points=3
                ))
        
        return questions
    
    def score_quiz(
        self,
        skill: str,
        questions: List[Dict[str, Any]],
        answers: List[QuizAnswer]
    ) -> Tuple[float, int, int, List[QuizResult]]:
        """
        Score a quiz submission.
        Uses Gemini to interpret free-form answers for advanced questions.
        
        Args:
            skill: The skill being assessed
            questions: The quiz questions (with correct answers)
            answers: User's answers
        
        Returns:
            Tuple of (score_percentage, points_earned, total_points, results)
        """
        skill_config = self._load_skill_config(skill)
        answer_key = self._build_answer_key(skill_config) if skill_config else {}
        
        answers_dict = {a.question_id: a.answer for a in answers}
        results: List[QuizResult] = []
        points_earned = 0
        total_points = 0
        
        client = get_client()
        
        for q in questions:
            q_id = q.get("question_id") or q.get("questionId")
            q_type = q.get("type", "multiple_choice")
            q_points = q.get("points", 1)
            total_points += q_points
            
            user_answer = answers_dict.get(q_id)
            
            # Check for correct answer: first in question data (Gemini), then in answer_key (config)
            correct_answer_value = q.get("correct_answer")
            explanation = q.get("explanation")
            
            if not correct_answer_value and q_id in answer_key:
                correct_answer_value = answer_key[q_id].get("answer")
                explanation = answer_key[q_id].get("explanation")
            
            if q_type == "text":
                # Use Gemini to interpret free-form answers
                result = self._score_text_answer_with_gemini(
                    client, q, user_answer, q_points
                )
                results.append(result)
                points_earned += result.points_earned
                
            elif correct_answer_value:
                # Multiple choice - exact match
                is_correct = str(user_answer).lower().strip() == str(correct_answer_value).lower().strip()
                
                earned = q_points if is_correct else 0
                points_earned += earned
                
                results.append(QuizResult(
                    question_id=q_id,
                    correct=is_correct,
                    points_earned=earned,
                    correct_answer=str(correct_answer_value),
                    explanation=explanation
                ))
            else:
                # No answer key - give partial credit for attempt
                is_correct = bool(user_answer)
                earned = q_points // 2 if user_answer else 0
                points_earned += earned
                
                results.append(QuizResult(
                    question_id=q_id,
                    correct=is_correct,
                    points_earned=earned,
                    correct_answer=None,
                    explanation="No answer key available for this question."
                ))
        
        score_percentage = (points_earned / total_points * 100) if total_points > 0 else 0
        
        return score_percentage, points_earned, total_points, results
    
    def _score_text_answer_with_gemini(
        self,
        client,
        question: Dict[str, Any],
        user_answer: str,
        max_points: int
    ) -> QuizResult:
        """
        Use Gemini to score a free-form text answer.
        
        Args:
            client: Gemini client
            question: The question data
            user_answer: User's text answer
            max_points: Maximum points for the question
        
        Returns:
            QuizResult with Gemini's interpretation
        """
        q_id = question.get("question_id") or question.get("questionId")
        prompt = question.get("prompt", "")
        expected_concepts = question.get("expected_concepts", [])
        
        if not user_answer or not user_answer.strip():
            return QuizResult(
                question_id=q_id,
                correct=False,
                points_earned=0,
                correct_answer=None,
                explanation="No answer provided."
            )
        
        try:
            # Use Gemini to interpret the answer
            interpretation = client.interpret_quiz_answer(
                question=prompt,
                expected_concepts=expected_concepts if expected_concepts else ["relevant concepts", "clear explanation", "technical accuracy"],
                user_answer=user_answer
            )
            
            score_pct = interpretation.get("score_percentage", 50)
            is_correct = interpretation.get("is_correct", score_pct >= 70)
            
            # Calculate points based on score percentage
            earned = int((score_pct / 100) * max_points)
            
            feedback = interpretation.get("feedback", "")
            concepts_found = interpretation.get("concepts_demonstrated", [])
            concepts_missing = interpretation.get("concepts_missing", [])
            
            explanation_parts = [feedback]
            if concepts_found:
                explanation_parts.append(f"Concepts demonstrated: {', '.join(concepts_found)}")
            if concepts_missing:
                explanation_parts.append(f"Could improve: {', '.join(concepts_missing)}")
            
            return QuizResult(
                question_id=q_id,
                correct=is_correct,
                points_earned=earned,
                correct_answer=None,
                explanation=" | ".join(explanation_parts)
            )
            
        except Exception as e:
            # Fallback if Gemini fails - give partial credit for attempt
            return QuizResult(
                question_id=q_id,
                correct=len(user_answer) > 50,
                points_earned=max_points // 2,
                correct_answer=None,
                explanation=f"Answer recorded. Detailed feedback unavailable: {str(e)}"
            )
    
    def _build_answer_key(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build answer key from skill configuration."""
        answer_key = {}
        quiz_bank = config.get("quiz_questions", {})
        
        for level_questions in quiz_bank.values():
            for q in level_questions:
                if "correct_answer" in q:
                    answer_key[q["question_id"]] = {
                        "answer": q["correct_answer"],
                        "explanation": q.get("explanation", ""),
                        "expected_concepts": q.get("expected_concepts", [])
                    }
        
        return answer_key


quiz_generator_service = QuizGeneratorService()
