"""
Questionnaire generation service.
Creates adaptive questionnaires based on the selected skill.
"""

import json
import os
from typing import List, Dict, Any, Optional
from ..models.schemas import Question, QuestionOption, QuestionType, LearningModality
from ..config import SKILLS_CONFIG_DIR


class QuestionnaireService:
    """Service for generating and managing questionnaires."""
    
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
            # Try to find a partial match
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
    
    def get_available_skills(self) -> List[str]:
        """Get list of available skills with configurations."""
        skills = []
        if os.path.exists(SKILLS_CONFIG_DIR):
            for filename in os.listdir(SKILLS_CONFIG_DIR):
                if filename.endswith('.json'):
                    with open(os.path.join(SKILLS_CONFIG_DIR, filename), 'r') as f:
                        config = json.load(f)
                        skills.append(config.get('skill_name', filename.replace('.json', '')))
        return skills
    
    def generate_questionnaire(self, skill: str) -> List[Question]:
        """
        Generate a questionnaire for the given skill.
        Returns 10-15 questions covering role, goals, self-assessment, and preferences.
        """
        questions: List[Question] = []
        skill_config = self._load_skill_config(skill)
        
        # Section 1: Role and Background (3 questions)
        questions.extend(self._generate_background_questions())
        
        # Section 2: Prior Exposure to Skill (1-2 questions)
        questions.extend(self._generate_exposure_questions(skill))
        
        # Section 3: Learning Goals (2 questions)
        questions.extend(self._generate_goal_questions(skill))
        
        # Section 4: Self-Assessment of Sub-skills (varies by skill, typically 5-7)
        if skill_config:
            questions.extend(self._generate_self_assessment_questions(skill_config))
        else:
            questions.extend(self._generate_generic_self_assessment(skill))
        
        # Section 5: Preferred Learning Modalities (1 question)
        questions.append(self._generate_modality_question())
        
        # Section 6: Time Availability (1 question)
        questions.append(self._generate_time_question())
        
        # Section 7: Open-ended (1 optional question)
        questions.append(self._generate_open_question(skill))
        
        return questions
    
    def _generate_background_questions(self) -> List[Question]:
        """Generate role and background questions."""
        return [
            Question(
                question_id="job_title",
                type=QuestionType.TEXT,
                prompt="What is your current job title or role?",
                category="background",
                required=False,
                options=[
                    QuestionOption(value="na", label="Not applicable / Prefer not to say")
                ]
            ),
            Question(
                question_id="experience_years",
                type=QuestionType.MULTIPLE_CHOICE,
                prompt="How many years of professional experience do you have?",
                category="background",
                required=True,
                options=[
                    QuestionOption(value="0", label="Student / No professional experience"),
                    QuestionOption(value="1", label="Less than 1 year"),
                    QuestionOption(value="2", label="1-2 years"),
                    QuestionOption(value="5", label="3-5 years"),
                    QuestionOption(value="10", label="6-10 years"),
                    QuestionOption(value="15", label="More than 10 years"),
                    QuestionOption(value="na", label="Not applicable")
                ]
            ),
            Question(
                question_id="education_level",
                type=QuestionType.MULTIPLE_CHOICE,
                prompt="What is your highest level of education?",
                category="background",
                required=False,
                options=[
                    QuestionOption(value="high_school", label="High School"),
                    QuestionOption(value="associate", label="Associate's Degree"),
                    QuestionOption(value="bachelor", label="Bachelor's Degree"),
                    QuestionOption(value="master", label="Master's Degree"),
                    QuestionOption(value="doctorate", label="Doctorate"),
                    QuestionOption(value="self_taught", label="Self-taught / Bootcamp"),
                    QuestionOption(value="na", label="Prefer not to say")
                ]
            )
        ]
    
    def _generate_exposure_questions(self, skill: str) -> List[Question]:
        """Generate prior exposure questions."""
        return [
            Question(
                question_id="prior_exposure",
                type=QuestionType.MULTIPLE_CHOICE,
                prompt=f"What is your prior experience with {skill}?",
                category="exposure",
                required=True,
                options=[
                    QuestionOption(value="none", label="No prior experience"),
                    QuestionOption(value="heard", label="I've heard about it but never used it"),
                    QuestionOption(value="tutorials", label="Completed some tutorials or courses"),
                    QuestionOption(value="projects", label="Built personal projects"),
                    QuestionOption(value="professional", label="Used professionally at work"),
                    QuestionOption(value="expert", label="Considered an expert / teach others")
                ]
            ),
            Question(
                question_id="related_skills",
                type=QuestionType.MULTI_SELECT,
                prompt="Do you have experience with any related skills? (Select all that apply)",
                category="exposure",
                required=False,
                options=[
                    QuestionOption(value="programming", label="Other programming languages"),
                    QuestionOption(value="web", label="Web development"),
                    QuestionOption(value="data", label="Data analysis / Statistics"),
                    QuestionOption(value="databases", label="Databases / SQL"),
                    QuestionOption(value="cloud", label="Cloud services (AWS, GCP, Azure)"),
                    QuestionOption(value="none", label="None of the above"),
                    QuestionOption(value="na", label="Not applicable")
                ]
            )
        ]
    
    def _generate_goal_questions(self, skill: str) -> List[Question]:
        """Generate learning goal questions."""
        return [
            Question(
                question_id="learning_reason",
                type=QuestionType.MULTI_SELECT,
                prompt=f"Why do you want to learn {skill}? (Select all that apply)",
                category="goals",
                required=True,
                options=[
                    QuestionOption(value="career", label="Career advancement / Job requirement"),
                    QuestionOption(value="new_job", label="Preparing for a new job or career change"),
                    QuestionOption(value="project", label="Specific project I want to build"),
                    QuestionOption(value="curiosity", label="Personal interest / Curiosity"),
                    QuestionOption(value="academic", label="Academic requirement / Course"),
                    QuestionOption(value="certification", label="Working toward a certification"),
                    QuestionOption(value="other", label="Other")
                ]
            ),
            Question(
                question_id="desired_outcome",
                type=QuestionType.MULTIPLE_CHOICE,
                prompt="What outcome do you hope to achieve?",
                category="goals",
                required=True,
                options=[
                    QuestionOption(value="basics", label="Understand the basics"),
                    QuestionOption(value="practical", label="Be able to apply it in practical situations"),
                    QuestionOption(value="proficient", label="Become proficient for professional work"),
                    QuestionOption(value="expert", label="Achieve expert-level mastery"),
                    QuestionOption(value="na", label="Not sure yet")
                ]
            )
        ]
    
    def _generate_self_assessment_questions(self, skill_config: Dict[str, Any]) -> List[Question]:
        """Generate self-assessment questions based on skill configuration."""
        questions = []
        sub_skills = skill_config.get("sub_skills", [])
        
        rating_options = [
            QuestionOption(value="1", label="1 - No knowledge"),
            QuestionOption(value="2", label="2 - Basic awareness"),
            QuestionOption(value="3", label="3 - Can apply with guidance"),
            QuestionOption(value="4", label="4 - Confident / Independent"),
            QuestionOption(value="5", label="5 - Expert / Can teach others"),
            QuestionOption(value="na", label="Not applicable / Haven't tried")
        ]
        
        for sub_skill in sub_skills:
            questions.append(Question(
                question_id=f"self_rating_{sub_skill['id']}",
                type=QuestionType.RATING,
                prompt=f"Rate your confidence with {sub_skill['name']}: {sub_skill['description']}",
                category="self_assessment",
                required=True,
                options=rating_options,
                sub_skill=sub_skill['id']
            ))
        
        return questions
    
    def _generate_generic_self_assessment(self, skill: str) -> List[Question]:
        """Generate generic self-assessment when no skill config exists."""
        rating_options = [
            QuestionOption(value="1", label="1 - No knowledge"),
            QuestionOption(value="2", label="2 - Basic awareness"),
            QuestionOption(value="3", label="3 - Can apply with guidance"),
            QuestionOption(value="4", label="4 - Confident / Independent"),
            QuestionOption(value="5", label="5 - Expert / Can teach others"),
            QuestionOption(value="na", label="Not applicable")
        ]
        
        return [
            Question(
                question_id="self_rating_overall",
                type=QuestionType.RATING,
                prompt=f"Rate your overall confidence with {skill}",
                category="self_assessment",
                required=True,
                options=rating_options,
                sub_skill="overall"
            ),
            Question(
                question_id="self_rating_theory",
                type=QuestionType.RATING,
                prompt=f"Rate your understanding of {skill} theory and concepts",
                category="self_assessment",
                required=True,
                options=rating_options,
                sub_skill="theory"
            ),
            Question(
                question_id="self_rating_practical",
                type=QuestionType.RATING,
                prompt=f"Rate your ability to apply {skill} in practice",
                category="self_assessment",
                required=True,
                options=rating_options,
                sub_skill="practical"
            )
        ]
    
    def _generate_modality_question(self) -> Question:
        """Generate learning modality preference question."""
        return Question(
            question_id="preferred_modalities",
            type=QuestionType.MULTI_SELECT,
            prompt="How do you prefer to learn? (Select all that apply)",
            category="preferences",
            required=True,
            options=[
                QuestionOption(value=LearningModality.VIDEO.value, label="Video tutorials and courses"),
                QuestionOption(value=LearningModality.ARTICLES.value, label="Articles and documentation"),
                QuestionOption(value=LearningModality.INTERACTIVE.value, label="Interactive exercises and coding challenges"),
                QuestionOption(value=LearningModality.PROJECTS.value, label="Hands-on projects"),
                QuestionOption(value=LearningModality.BOOKS.value, label="Books and long-form content"),
                QuestionOption(value=LearningModality.MENTORSHIP.value, label="Mentorship and live instruction")
            ]
        )
    
    def _generate_time_question(self) -> Question:
        """Generate time availability question."""
        return Question(
            question_id="time_availability",
            type=QuestionType.MULTIPLE_CHOICE,
            prompt="How much time can you dedicate to learning per week?",
            category="preferences",
            required=True,
            options=[
                QuestionOption(value="1", label="Less than 1 hour"),
                QuestionOption(value="3", label="1-3 hours"),
                QuestionOption(value="5", label="3-5 hours"),
                QuestionOption(value="10", label="5-10 hours"),
                QuestionOption(value="20", label="10-20 hours"),
                QuestionOption(value="40", label="More than 20 hours (full-time)")
            ]
        )
    
    def _generate_open_question(self, skill: str) -> Question:
        """Generate open-ended question."""
        return Question(
            question_id="open_projects",
            type=QuestionType.TEXT,
            prompt=f"(Optional) Describe any recent projects or specific challenges related to {skill} that you'd like to work on:",
            category="open_ended",
            required=False,
            options=None
        )


questionnaire_service = QuestionnaireService()
