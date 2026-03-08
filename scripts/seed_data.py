"""
Seed data generator for testing the learning system.
Generates 100+ synthetic learner profiles with mocked Gemini responses.

This script allows testing classification and recommendation flows
WITHOUT requiring a Gemini API key.

Usage:
    python -m scripts.seed_data [--count 100] [--validate]
"""

import asyncio
import argparse
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
import numpy as np

from app.models.schemas import SkillLevel, QuestionnaireAnswer
from app.services.gemini_client import MockGeminiClient, set_client, get_client
from app.services.classification import classification_service
from app.services.recommendations import recommendation_service

fake = Faker()


# ============== Mock Gemini Responses ==============

MOCK_CLASSIFICATION_RESPONSES = {
    "beginner": {
        "level": "beginner",
        "confidence": 0.85,
        "reasoning": [
            "Low self-assessment scores indicate limited practical experience",
            "No prior professional exposure to the skill",
            "Learning goals focused on understanding fundamentals",
            "Recommend starting with beginner-friendly content"
        ]
    },
    "intermediate": {
        "level": "intermediate",
        "confidence": 0.82,
        "reasoning": [
            "Moderate self-assessment scores show foundational knowledge",
            "Has completed tutorials or personal projects",
            "Can apply concepts but needs guidance for complex tasks",
            "Ready for application-focused learning"
        ]
    },
    "advanced": {
        "level": "advanced",
        "confidence": 0.88,
        "reasoning": [
            "High self-assessment scores indicate strong proficiency",
            "Significant professional or teaching experience",
            "Can innovate and mentor others",
            "Ready for advanced topics and specialization"
        ]
    }
}

MOCK_RECOMMENDATION_RESPONSES = {
    "beginner": [
        {
            "title": "Complete Beginner's Guide - Full Course",
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=mock_beginner_1",
            "difficulty": "beginner",
            "duration_hours": 6.0,
            "is_free": True,
            "price": "Free",
            "rating": 4.8,
            "why_recommended": "Comprehensive introduction perfect for beginners",
            "snippet_start": None,
            "snippet_end": None
        },
        {
            "title": "Fundamentals Specialization",
            "platform": "coursera",
            "url": "https://www.coursera.org/specializations/mock-fundamentals",
            "difficulty": "beginner",
            "duration_hours": 40,
            "is_free": False,
            "price": "$49/month (free audit available)",
            "rating": 4.7,
            "why_recommended": "University-backed curriculum for solid foundation",
            "snippet_start": None,
            "snippet_end": None
        }
    ],
    "intermediate": [
        {
            "title": "Intermediate Masterclass - Real Projects",
            "platform": "udemy",
            "url": "https://www.udemy.com/course/mock-intermediate",
            "difficulty": "intermediate",
            "duration_hours": 25,
            "is_free": False,
            "price": "$14.99 on sale",
            "rating": 4.6,
            "why_recommended": "Project-based learning for practical skills",
            "snippet_start": None,
            "snippet_end": None
        },
        {
            "title": "Deep Dive Tutorial Series",
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=mock_intermediate_1",
            "difficulty": "intermediate",
            "duration_hours": 8.0,
            "is_free": True,
            "price": "Free",
            "rating": 4.5,
            "why_recommended": "In-depth coverage of intermediate concepts",
            "snippet_start": 120,
            "snippet_end": 3600
        }
    ],
    "advanced": [
        {
            "title": "Advanced Patterns and Architecture",
            "platform": "udemy",
            "url": "https://www.udemy.com/course/mock-advanced",
            "difficulty": "advanced",
            "duration_hours": 15,
            "is_free": False,
            "price": "$19.99 on sale",
            "rating": 4.7,
            "why_recommended": "Expert-level patterns and best practices",
            "snippet_start": None,
            "snippet_end": None
        },
        {
            "title": "Professional Certificate",
            "platform": "coursera",
            "url": "https://www.coursera.org/professional-certificates/mock-advanced",
            "difficulty": "advanced",
            "duration_hours": 80,
            "is_free": False,
            "price": "$49/month",
            "rating": 4.8,
            "why_recommended": "Industry-recognized certification for experts",
            "snippet_start": None,
            "snippet_end": None
        }
    ]
}

MOCK_QUIZ_INTERPRETATIONS = {
    "good": {
        "score_percentage": 85,
        "concepts_demonstrated": ["clear explanation", "technical accuracy", "practical examples"],
        "concepts_missing": [],
        "feedback": "Excellent answer! You demonstrated strong understanding of the concepts.",
        "is_correct": True
    },
    "partial": {
        "score_percentage": 60,
        "concepts_demonstrated": ["basic understanding", "some technical terms"],
        "concepts_missing": ["depth of explanation", "practical application"],
        "feedback": "Good start, but could be more detailed. Consider adding practical examples.",
        "is_correct": False
    },
    "poor": {
        "score_percentage": 30,
        "concepts_demonstrated": ["attempted response"],
        "concepts_missing": ["technical accuracy", "clear explanation", "relevant concepts"],
        "feedback": "The answer needs improvement. Review the core concepts and try again.",
        "is_correct": False
    }
}


class MockGeminiClientWithProfiles(MockGeminiClient):
    """
    Enhanced mock client that returns appropriate responses based on profile.
    Used for testing the full flow without API key.
    """
    
    def __init__(self, target_level: str = None):
        super().__init__()
        self.target_level = target_level
    
    def classify_skill_level(
        self,
        skill: str,
        questionnaire_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return mock classification based on self-ratings."""
        self.call_log.append({
            "method": "classify_skill_level",
            "skill": skill,
            "responses_count": len(questionnaire_responses)
        })
        
        # If target level is set, use it
        if self.target_level:
            return MOCK_CLASSIFICATION_RESPONSES[self.target_level]
        
        # Otherwise, determine from responses
        ratings = []
        for key, value in questionnaire_responses.items():
            if key.startswith("self_rating_") and value not in ["na", None]:
                try:
                    ratings.append(float(value))
                except (ValueError, TypeError):
                    pass
        
        if ratings:
            mean_rating = sum(ratings) / len(ratings)
            if mean_rating < 2.5:
                return MOCK_CLASSIFICATION_RESPONSES["beginner"]
            elif mean_rating < 4.0:
                return MOCK_CLASSIFICATION_RESPONSES["intermediate"]
            else:
                return MOCK_CLASSIFICATION_RESPONSES["advanced"]
        
        return MOCK_CLASSIFICATION_RESPONSES["beginner"]
    
    def get_course_recommendations(
        self,
        skill: str,
        level: str,
        preferred_modalities: List[str],
        interests: str = None
    ) -> List[Dict[str, Any]]:
        """Return mock recommendations for the level."""
        self.call_log.append({
            "method": "get_course_recommendations",
            "skill": skill,
            "level": level
        })
        
        recommendations = MOCK_RECOMMENDATION_RESPONSES.get(level, MOCK_RECOMMENDATION_RESPONSES["intermediate"])
        
        # Customize titles with skill name
        customized = []
        for rec in recommendations:
            custom_rec = rec.copy()
            if skill.lower() not in custom_rec["title"].lower():
                custom_rec["title"] = f"{skill} - {custom_rec['title']}"
            customized.append(custom_rec)
        
        return customized
    
    def interpret_quiz_answer(
        self,
        question: str,
        expected_concepts: List[str],
        user_answer: str
    ) -> Dict[str, Any]:
        """Return mock interpretation based on answer length."""
        self.call_log.append({
            "method": "interpret_quiz_answer",
            "answer_length": len(user_answer) if user_answer else 0
        })
        
        if not user_answer or len(user_answer) < 20:
            return MOCK_QUIZ_INTERPRETATIONS["poor"]
        elif len(user_answer) < 100:
            return MOCK_QUIZ_INTERPRETATIONS["partial"]
        else:
            return MOCK_QUIZ_INTERPRETATIONS["good"]


class SyntheticLearnerGenerator:
    """Generates synthetic learner profiles for testing."""
    
    SKILLS = [
        "Python programming",
        "JavaScript",
        "Data Science",
        "Web Development",
        "Machine Learning"
    ]
    
    JOB_TITLES = [
        "Student", "Junior Developer", "Software Developer", "Senior Developer",
        "Data Analyst", "Data Scientist", "Product Manager", "Designer",
        "QA Engineer", "DevOps Engineer", "Technical Lead", "Architect",
        "Career Changer", "Freelancer", "Entrepreneur"
    ]
    
    PRIOR_EXPOSURE_OPTIONS = ["none", "heard", "tutorials", "projects", "professional", "expert"]
    LEARNING_REASONS = ["career", "new_job", "project", "curiosity", "academic", "certification"]
    DESIRED_OUTCOMES = ["basics", "practical", "proficient", "expert"]
    MODALITIES = ["video", "articles", "interactive_exercises", "hands_on_projects", "books", "mentorship"]
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)
    
    def generate_profile(self, target_level: SkillLevel = None) -> Dict[str, Any]:
        """Generate a single synthetic learner profile."""
        if target_level is None:
            target_level = random.choice(list(SkillLevel))
        
        profile = {
            "target_level": target_level.value,
            "skill": random.choice(self.SKILLS),
            "questionnaire_responses": self._generate_questionnaire_responses(target_level),
            "expected_quiz_performance": self._generate_quiz_performance(target_level),
            "mock_gemini_response": MOCK_CLASSIFICATION_RESPONSES[target_level.value],
            "created_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat()
        }
        
        return profile
    
    def _generate_questionnaire_responses(self, level: SkillLevel) -> Dict[str, Any]:
        """Generate questionnaire responses consistent with the target level."""
        responses = {}
        
        if level == SkillLevel.BEGINNER:
            responses["job_title"] = random.choice(["Student", "Career Changer", "Junior Developer", "Intern"])
            responses["experience_years"] = str(random.choice([0, 1, 2]))
            responses["prior_exposure"] = random.choice(["none", "heard", "tutorials"])
            mean_rating = random.uniform(1.5, 2.3)
            std_dev = 0.5
        elif level == SkillLevel.INTERMEDIATE:
            responses["job_title"] = random.choice(["Software Developer", "Data Analyst", "QA Engineer"])
            responses["experience_years"] = str(random.choice([2, 5, 5]))
            responses["prior_exposure"] = random.choice(["tutorials", "projects", "professional"])
            mean_rating = random.uniform(2.8, 3.8)
            std_dev = 0.7
        else:
            responses["job_title"] = random.choice(["Senior Developer", "Technical Lead", "Architect"])
            responses["experience_years"] = str(random.choice([5, 10, 15]))
            responses["prior_exposure"] = random.choice(["professional", "expert"])
            mean_rating = random.uniform(4.2, 4.8)
            std_dev = 0.4
        
        sub_skills = ["basic_syntax", "control_flow", "data_structures", "functions",
                     "modules", "file_io", "oop", "advanced_patterns", "async_programming", "testing"]
        
        for sub_skill in sub_skills:
            rating = np.clip(np.random.normal(mean_rating, std_dev), 1, 5)
            if level == SkillLevel.BEGINNER and sub_skill in ["advanced_patterns", "async_programming", "testing"]:
                if random.random() < 0.3:
                    responses[f"self_rating_{sub_skill}"] = "na"
                    continue
            responses[f"self_rating_{sub_skill}"] = str(int(round(rating)))
        
        responses["learning_reason"] = random.sample(self.LEARNING_REASONS, k=random.randint(1, 3))
        
        if level == SkillLevel.BEGINNER:
            responses["desired_outcome"] = random.choice(["basics", "practical"])
        elif level == SkillLevel.INTERMEDIATE:
            responses["desired_outcome"] = random.choice(["practical", "proficient"])
        else:
            responses["desired_outcome"] = random.choice(["proficient", "expert"])
        
        responses["preferred_modalities"] = random.sample(self.MODALITIES, k=random.randint(1, 3))
        responses["time_availability"] = str(random.choice([1, 3, 5, 10, 20]))
        
        if random.random() < 0.4:
            responses["open_projects"] = fake.sentence(nb_words=15)
        
        return responses
    
    def _generate_quiz_performance(self, level: SkillLevel) -> Dict[str, Any]:
        """Generate expected quiz performance for the level."""
        if level == SkillLevel.BEGINNER:
            return {
                "beginner_quiz_score": round(random.uniform(50, 85), 1),
                "intermediate_quiz_score": round(random.uniform(20, 50), 1),
                "advanced_quiz_score": round(random.uniform(10, 30), 1)
            }
        elif level == SkillLevel.INTERMEDIATE:
            return {
                "beginner_quiz_score": round(random.uniform(75, 95), 1),
                "intermediate_quiz_score": round(random.uniform(55, 85), 1),
                "advanced_quiz_score": round(random.uniform(30, 55), 1)
            }
        else:
            return {
                "beginner_quiz_score": round(random.uniform(90, 100), 1),
                "intermediate_quiz_score": round(random.uniform(80, 95), 1),
                "advanced_quiz_score": round(random.uniform(65, 90), 1)
            }
    
    def generate_profiles(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate multiple synthetic profiles with balanced level distribution."""
        profiles = []
        levels = list(SkillLevel)
        per_level = count // len(levels)
        remainder = count % len(levels)
        
        for i, level in enumerate(levels):
            level_count = per_level + (1 if i < remainder else 0)
            for _ in range(level_count):
                profiles.append(self.generate_profile(level))
        
        random.shuffle(profiles)
        return profiles


def validate_classification_with_mock(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate classification using mocked Gemini responses.
    Tests that the system correctly processes Gemini's responses.
    """
    results = {
        "total": len(profiles),
        "correct": 0,
        "incorrect": 0,
        "confusion_matrix": {
            "beginner": {"beginner": 0, "intermediate": 0, "advanced": 0},
            "intermediate": {"beginner": 0, "intermediate": 0, "advanced": 0},
            "advanced": {"beginner": 0, "intermediate": 0, "advanced": 0}
        },
        "gemini_calls": 0,
        "sample_responses": []
    }
    
    for profile in profiles:
        expected_level = profile["target_level"]
        responses = profile["questionnaire_responses"]
        skill = profile["skill"]
        
        # Set up mock client for this profile's expected level
        mock_client = MockGeminiClientWithProfiles(target_level=expected_level)
        set_client(mock_client)
        
        # Convert to QuestionnaireAnswer objects
        answers = [
            QuestionnaireAnswer(question_id=k, answer=v)
            for k, v in responses.items()
        ]
        
        # Classify using the service (which will use our mock)
        predicted_level, explanation = classification_service.classify(answers, skill)
        
        # Track Gemini calls
        results["gemini_calls"] += len(mock_client.call_log)
        
        # Track results
        results["confusion_matrix"][expected_level][predicted_level.value] += 1
        
        if predicted_level.value == expected_level:
            results["correct"] += 1
        else:
            results["incorrect"] += 1
        
        # Save sample responses
        if len(results["sample_responses"]) < 5:
            results["sample_responses"].append({
                "expected": expected_level,
                "predicted": predicted_level.value,
                "confidence": explanation.confidence,
                "reasoning_sample": explanation.factors[:2] if explanation.factors else []
            })
    
    results["accuracy"] = (results["correct"] / results["total"] * 100) if results["total"] > 0 else 0
    
    return results


def validate_recommendations_with_mock(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate recommendations using mocked Gemini responses.
    """
    results = {
        "total_profiles": len(profiles),
        "recommendations_generated": 0,
        "gemini_calls": 0,
        "platform_distribution": {"youtube": 0, "coursera": 0, "udemy": 0},
        "sample_recommendations": []
    }
    
    for profile in profiles[:20]:
        level = profile["target_level"]
        skill = profile["skill"]
        
        # Set up mock client
        mock_client = MockGeminiClientWithProfiles(target_level=level)
        set_client(mock_client)
        
        # Get recommendations
        recommendations = recommendation_service.get_recommendations(
            skill=skill,
            level=SkillLevel(level),
            limit=3
        )
        
        results["gemini_calls"] += len(mock_client.call_log)
        
        if recommendations:
            results["recommendations_generated"] += 1
            
            for rec in recommendations:
                results["platform_distribution"][rec.platform.value] += 1
        
        if len(results["sample_recommendations"]) < 5 and recommendations:
            results["sample_recommendations"].append({
                "skill": skill,
                "level": level,
                "recommendations": [
                    {
                        "title": r.title,
                        "platform": r.platform.value,
                        "difficulty": r.difficulty.value,
                        "is_free": r.is_free
                    }
                    for r in recommendations
                ]
            })
    
    return results


def main():
    """Main entry point for seed data generation with mocked Gemini."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic learner profiles with mocked Gemini responses"
    )
    parser.add_argument("--count", type=int, default=100, help="Number of profiles to generate")
    parser.add_argument("--validate", action="store_true", help="Validate with mocked Gemini")
    parser.add_argument("--output", type=str, default="seed_data.json", help="Output file path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SEED DATA GENERATOR WITH MOCKED GEMINI RESPONSES")
    print("=" * 60)
    print("\nThis script tests the learning system WITHOUT requiring a Gemini API key.")
    print("Mock responses simulate Gemini's classification and recommendation behavior.\n")
    
    print(f"Generating {args.count} synthetic learner profiles...")
    
    generator = SyntheticLearnerGenerator(seed=args.seed)
    profiles = generator.generate_profiles(args.count)
    
    # Count by level
    level_counts = {}
    for profile in profiles:
        level = profile["target_level"]
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\nProfile distribution:")
    for level, count in sorted(level_counts.items()):
        print(f"  {level}: {count}")
    
    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), args.output)
    with open(output_path, 'w') as f:
        json.dump(profiles, f, indent=2)
    print(f"\nProfiles saved to {output_path}")
    
    # Also save mock responses for reference
    mock_responses_path = os.path.join(os.path.dirname(__file__), "mock_gemini_responses.json")
    with open(mock_responses_path, 'w') as f:
        json.dump({
            "classification_responses": MOCK_CLASSIFICATION_RESPONSES,
            "recommendation_responses": MOCK_RECOMMENDATION_RESPONSES,
            "quiz_interpretations": MOCK_QUIZ_INTERPRETATIONS
        }, f, indent=2)
    print(f"Mock Gemini responses saved to {mock_responses_path}")
    
    # Validate if requested
    if args.validate:
        print("\n" + "=" * 60)
        print("CLASSIFICATION VALIDATION (with Mocked Gemini)")
        print("=" * 60)
        
        classification_results = validate_classification_with_mock(profiles)
        
        print(f"\nAccuracy: {classification_results['accuracy']:.1f}%")
        print(f"Correct: {classification_results['correct']}/{classification_results['total']}")
        print(f"Gemini API calls made (mocked): {classification_results['gemini_calls']}")
        
        print("\nConfusion Matrix:")
        print("                  Predicted")
        print("                  Beginner  Intermediate  Advanced")
        for actual in ["beginner", "intermediate", "advanced"]:
            row = classification_results["confusion_matrix"][actual]
            print(f"Actual {actual:12s}  {row['beginner']:8d}  {row['intermediate']:12d}  {row['advanced']:8d}")
        
        if classification_results["sample_responses"]:
            print("\nSample Gemini responses:")
            for sample in classification_results["sample_responses"][:3]:
                print(f"  Expected: {sample['expected']}, Got: {sample['predicted']}, "
                      f"Confidence: {sample['confidence']:.2f}")
                if sample['reasoning_sample']:
                    print(f"    Reasoning: {sample['reasoning_sample'][0]}")
        
        print("\n" + "=" * 60)
        print("RECOMMENDATION VALIDATION (with Mocked Gemini)")
        print("=" * 60)
        
        rec_results = validate_recommendations_with_mock(profiles)
        
        print(f"\nProfiles with recommendations: {rec_results['recommendations_generated']}")
        print(f"Gemini API calls made (mocked): {rec_results['gemini_calls']}")
        
        print(f"\nPlatform distribution:")
        for platform, count in rec_results["platform_distribution"].items():
            print(f"  {platform}: {count}")
        
        if rec_results["sample_recommendations"]:
            print("\nSample recommendations:")
            for sample in rec_results["sample_recommendations"][:3]:
                print(f"\n  Skill: {sample['skill']}, Level: {sample['level']}")
                for rec in sample["recommendations"]:
                    free_label = "FREE" if rec["is_free"] else "PAID"
                    print(f"    - [{free_label}] {rec['title'][:40]}... ({rec['platform']})")
    
    print("\n" + "=" * 60)
    print("DONE - All tests used MOCKED Gemini responses")
    print("=" * 60)


if __name__ == "__main__":
    main()
