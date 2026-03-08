# Personalized Learning System - Complete Project Context

## 1. PROJECT OVERVIEW

This is a **FastAPI-based personalized learning system** that:
1. Assesses a user's skill level (Beginner/Intermediate/Advanced) using AI
2. Generates diagnostic quizzes
3. Provides personalized course recommendations from YouTube, Coursera, and Udemy
4. Assigns a skill score (1-10) based on quiz performance

### Tech Stack
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy (async), SQLite
- **AI**: Google Gemini API (gemini-2.5-flash model)
- **Frontend**: Vanilla HTML/CSS/JavaScript (single-page app)
- **Database**: SQLite with aiosqlite for async operations

---

## 2. PROJECT STRUCTURE

```
HACKAI 26/
├── app/
│   ├── __init__.py              # Version info
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings (env vars, thresholds)
│   ├── models/
│   │   ├── database.py          # SQLAlchemy models & DB setup
│   │   └── schemas.py           # Pydantic schemas for API
│   ├── routers/
│   │   ├── sessions.py          # POST /sessions/start
│   │   ├── questionnaire.py     # POST /questionnaire/submit
│   │   ├── quiz.py              # GET/POST /quiz endpoints
│   │   ├── resources.py         # GET /resources/{id}/recommendations
│   │   ├── concept_map.py       # GET /concept-map/{skill}
│   │   ├── practice.py          # Scenario practice endpoints
│   │   └── privacy.py           # Data privacy endpoints
│   ├── services/
│   │   ├── gemini_client.py     # Gemini API client (Real + Mock)
│   │   ├── quiz_generator.py    # Quiz generation & scoring
│   │   ├── recommendations.py   # Course recommendation service
│   │   ├── classification.py    # Skill level classification
│   │   ├── questionnaire.py     # Questionnaire generation
│   │   ├── concept_map.py       # Concept map generation
│   │   └── scenario.py          # Scenario practice service
│   └── data/
│       └── skills/              # JSON configs for specific skills
├── frontend/
│   ├── index.html               # Main HTML page
│   ├── styles.css               # CSS styling
│   └── app.js                   # JavaScript logic
├── .env                         # Environment variables (API keys)
├── requirements.txt             # Python dependencies
└── learning_system.db           # SQLite database (auto-created)
```

---

## 3. KEY CONFIGURATION

### .env File
```
GEMINI_API_KEY=your_api_key_here
DEBUG=false
```

### config.py Settings
```python
class Settings:
    database_url = "sqlite+aiosqlite:///./learning_system.db"
    gemini_api_key = None  # From .env
    min_quiz_questions = 5
    max_quiz_questions = 10
    upgrade_score_threshold = 0.85  # 85% to upgrade level
    downgrade_score_threshold = 0.4  # 40% to downgrade level
```

---

## 4. USER FLOW & API ENDPOINTS

### Flow Diagram
```
[1. Start Session] → [2. Questionnaire] → [3. Classification] → [4. Quiz] → [5. Recommendations]
```

### API Endpoints (all prefixed with `/api/v1`)

| Step | Endpoint | Method | Description |
|------|----------|--------|-------------|
| 1 | `/sessions/start` | POST | Start session, get questionnaire |
| 2 | `/questionnaire/submit` | POST | Submit answers, get skill level |
| 3 | `/quiz/{session_id}` | GET | Get diagnostic quiz |
| 4 | `/quiz/submit` | POST | Submit quiz, get score & skill_score |
| 5 | `/resources/{session_id}/recommendations` | GET | Get course recommendations |

### Request/Response Examples

**1. Start Session**
```json
// POST /api/v1/sessions/start
// Request:
{ "skill": "React" }

// Response:
{
  "session_id": "uuid-here",
  "skill": "React",
  "questionnaire": [
    {
      "question_id": "self_rating_1",
      "prompt": "Rate your confidence with React basics (1-5)",
      "options": [{"value": "1", "label": "No knowledge"}, ...]
    }
  ]
}
```

**2. Submit Questionnaire**
```json
// POST /api/v1/questionnaire/submit
// Request:
{
  "session_id": "uuid-here",
  "answers": [
    {"question_id": "self_rating_1", "answer": "2"},
    {"question_id": "prior_exposure", "answer": "tutorials"}
  ]
}

// Response:
{
  "session_id": "uuid-here",
  "assigned_level": "beginner",
  "explanation": {
    "confidence": 0.85,
    "factors": ["Low self-rating", "Limited prior exposure"]
  }
}
```

**3. Get Quiz**
```json
// GET /api/v1/quiz/{session_id}?num_questions=5

// Response:
{
  "quiz_id": "quiz-uuid",
  "questions": [
    {
      "question_id": "gen_beginner_1",
      "prompt": "What is the primary purpose of React?",
      "options": [
        {"value": "a", "label": "To build user interfaces"},
        {"value": "b", "label": "To manage databases"},
        ...
      ],
      "correct_answer": "a"  // Stored but hidden from user display
    }
  ]
}
```

**4. Submit Quiz**
```json
// POST /api/v1/quiz/submit
// Request:
{
  "session_id": "uuid",
  "quiz_id": "quiz-uuid",
  "answers": [
    {"question_id": "gen_beginner_1", "answer": "a"}
  ]
}

// Response:
{
  "score": 80.0,
  "score_percentage": 80.0,
  "skill_score": 3,  // 1-10 scale
  "points_earned": 4,
  "total_points": 5,
  "feedback": "Good performance! ..."
}
```

**5. Get Recommendations**
```json
// GET /api/v1/resources/{session_id}/recommendations?limit=6

// Response:
{
  "recommendations": [
    {
      "title": "React Beginner Tutorial",
      "platform": "youtube",
      "url": "https://www.youtube.com/results?search_query=React+beginner+tutorial",
      "difficulty": "beginner",
      "is_free": true,
      "why_recommended": "Perfect for beginners..."
    }
  ]
}
```

---

## 5. GEMINI CLIENT ARCHITECTURE

### Two Implementations

```
GeminiClientBase (Abstract)
    ├── GeminiClient (Real API)
    │   - Uses actual Gemini API
    │   - Model: gemini-2.5-flash
    │   - Requires GEMINI_API_KEY
    │
    └── MockGeminiClient (Testing/Fallback)
        - Returns pre-defined responses
        - Used when API key missing or quota exceeded
```

### Client Selection Logic (gemini_client.py)
```python
_active_client: Optional[GeminiClientBase] = None

def get_client() -> GeminiClientBase:
    global _active_client
    if _active_client:
        return _active_client
    
    # Try real client first
    if settings.gemini_api_key:
        try:
            _active_client = GeminiClient()
            return _active_client
        except Exception:
            pass
    
    # Fall back to mock
    _active_client = MockGeminiClient()
    return _active_client
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `classify_skill_level(skill, responses)` | Determine beginner/intermediate/advanced |
| `generate_quiz_questions(skill, level, num)` | Create quiz questions |
| `get_course_recommendations(skill, level, ...)` | Get course suggestions |
| `interpret_quiz_answer(question, concepts, answer)` | Score text answers |

---

## 6. QUIZ SCORING LOGIC

### QuizQuestion Schema
```python
class QuizQuestion(BaseModel):
    question_id: str
    type: QuestionType
    prompt: str
    options: List[QuestionOption]
    difficulty: SkillLevel
    points: int = 1
    correct_answer: Optional[str]  # REQUIRED for scoring
    explanation: Optional[str]
```

### Scoring Flow (quiz_generator.py)
```python
def score_quiz(skill, questions, answers):
    for question in questions:
        correct_answer = question.get("correct_answer")
        user_answer = answers_dict.get(question_id)
        
        is_correct = user_answer.lower() == correct_answer.lower()
        points_earned += question["points"] if is_correct else 0
    
    score_percentage = (points_earned / total_points) * 100
    return score_percentage, points_earned, total_points, results
```

### Skill Score Calculation (1-10)
```python
# In routers/quiz.py submit_quiz()
if level == BEGINNER:
    base_score = 1  # Range: 1-3, up to 4 if 90%+
elif level == INTERMEDIATE:
    base_score = 4  # Range: 4-6, up to 7 if 90%+
else:  # ADVANCED
    base_score = 7  # Range: 7-9, up to 10 if 90%+

skill_score = base_score + (score_percentage / 100) * 3
if score_percentage >= 90:
    skill_score += 1  # Bonus point
```

---

## 7. RECOMMENDATION URL HANDLING

### Problem Solved
- Gemini API sometimes generates fake/broken URLs
- Specific video/course URLs can become unavailable

### Solution: Safe Search URLs
All URLs are converted to search result pages that always work:

```python
# In recommendations.py
def _ensure_safe_url(url, platform, title):
    search_terms = re.sub(r'[^\w\s]', '', title).strip()
    search_encoded = urllib.parse.quote_plus(search_terms)
    
    if platform == "youtube":
        if "/results?search_query=" not in url:
            return f"https://www.youtube.com/results?search_query={search_encoded}"
    
    elif platform == "coursera":
        if "/search?" not in url:
            return f"https://www.coursera.org/search?query={search_encoded}"
    
    elif platform == "udemy":
        if "/courses/search/?" not in url:
            return f"https://www.udemy.com/courses/search/?q={search_encoded}"
    
    return url
```

### URL Format by Platform
```
YouTube:  https://www.youtube.com/results?search_query=React+beginner+tutorial
Coursera: https://www.coursera.org/search?query=React&productDifficultyLevel=Beginner
Udemy:    https://www.udemy.com/courses/search/?q=React&instructional_level=beginner
```

---

## 8. FRONTEND STRUCTURE

### Key Functions (app.js)

| Function | Purpose |
|----------|---------|
| `startSession()` | POST to /sessions/start, get questionnaire |
| `submitQuestionnaire()` | POST answers, get classification |
| `startQuiz()` | GET quiz questions |
| `renderQuiz(questions)` | Display quiz UI |
| `submitQuiz()` | POST answers, display score + skill_score |
| `loadRecommendations()` | GET recommendations |
| `renderRecommendations(recs)` | Display recommendation cards |

### State Management
```javascript
let state = {
    sessionId: null,
    skill: null,
    questionnaire: [],
    currentLevel: null,  // "beginner" | "intermediate" | "advanced"
    quizId: null,
    quizQuestions: []
};
```

---

## 9. DATABASE MODELS

### Sessions Table
```python
class DBSession(Base):
    id: str  # Primary key (UUID)
    skill: str
    learner_name: str
    assigned_level: str
    questionnaire_answers: JSON
    created_at: datetime
    data_deleted: bool = False
```

### Quiz Table
```python
class DBQuiz(Base):
    id: str  # Primary key (UUID)
    session_id: str  # Foreign key
    target_level: str
    questions: JSON  # List of question dicts
    answers: JSON
    score: float
    points_earned: int
    total_points: int
    completed_at: datetime
    level_adjusted: bool
    new_level: str
```

---

## 10. KNOWN ISSUES & FIXES APPLIED

### Issue 1: Quiz Score Always 0%
**Cause**: `QuizQuestion` schema didn't have `correct_answer` field
**Fix**: Added `correct_answer` and `explanation` to schema

### Issue 2: Quiz Shows "undefined" Questions
**Cause**: Frontend using `q.question` instead of `q.prompt`
**Fix**: Updated to `q.prompt || q.question`

### Issue 3: Broken YouTube/Udemy Links
**Cause**: Gemini generates fake specific URLs
**Fix**: Convert all URLs to search URLs via `_ensure_safe_url()`

### Issue 4: Same Recommendations for All Levels
**Cause**: Mock client had identical recommendations
**Fix**: Created level-specific recommendation sets

---

## 11. RUNNING THE PROJECT

### Setup
```bash
cd "HACKAI 26"
pip install -r requirements.txt

# Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env
```

### Start Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access
- Frontend: http://localhost:8000/app
- API Docs: http://localhost:8000/docs
- API Root: http://localhost:8000/

---

## 12. DEBUGGING TIPS

### Check Server Logs
Server prints errors like:
```
Gemini quiz generation failed: [error], falling back to config
Warning: Gemini recommendation failed: [error]
```

### Test Mock Client
```python
from app.services.gemini_client import MockGeminiClient, set_client
client = MockGeminiClient()
set_client(client)

# Test quiz generation
questions = client.generate_quiz_questions("React", "beginner", 5)
print(questions[0]["prompt"], questions[0]["correct_answer"])
```

### Clear Database
Delete `learning_system.db` to reset all sessions/quizzes.

### Force Mock Client
Set `GEMINI_API_KEY=` (empty) in `.env` to always use mock.

---

## 13. FILE CONTENTS FOR REFERENCE

### requirements.txt
```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
python-multipart>=0.0.9
httpx>=0.26.0
sqlalchemy>=2.0.25
aiosqlite>=0.19.0
networkx>=3.2.0
matplotlib>=3.8.0
pillow>=10.0.0
numpy>=1.26.0
faker>=22.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
google-generativeai>=0.4.0
python-dotenv>=1.0.0
```

---

## 14. COMMON DEBUGGING SCENARIOS

### "Quiz score is 0% even with correct answers"
1. Check if `QuizQuestion` schema has `correct_answer` field
2. Verify quiz_generator.py includes `correct_answer` when creating questions
3. Check score_quiz() is comparing answers correctly

### "Recommendations link to non-existent pages"
1. Check `_ensure_safe_url()` in recommendations.py
2. Verify URLs are search URLs, not specific video/course URLs
3. Mock client should generate search URLs directly

### "Gemini API returns 404/429 errors"
1. 404: Model name may be deprecated (try gemini-2.5-flash)
2. 429: Quota exceeded - wait or use mock client
3. Check API key is valid and not expired

### "Frontend shows 'undefined' for questions"
1. Check quiz rendering uses `q.prompt || q.question`
2. Verify API response includes `prompt` field
3. Check browser console for JavaScript errors

---

This document provides complete context for debugging the Personalized Learning System. All code paths, data flows, and known issues are documented above.
