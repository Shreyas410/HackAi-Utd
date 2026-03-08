# Personalised Learning System API

A comprehensive back-end API for an adaptive learning system that uses **Gemini AI** to assess learner skill levels and provide personalized content recommendations based on the Dreyfus Model of Skill Acquisition.

## Features

### 🎯 Gemini-Powered Skill Assessment
- Dynamic questionnaire generation (10-15 questions)
- **Classification performed by Gemini API** (no local threshold logic)
- Dreyfus model levels: Beginner, Intermediate, Advanced

### 📝 Diagnostic Quizzes
- Level-appropriate quiz generation (5-10 questions)
- **Gemini interprets free-form answers** for advanced quizzes
- Automatic scoring with detailed feedback

### 🎮 Scenario-Based Practice
- Interactive scenarios with branching logic
- Decision points with consequences and feedback
- Complexity adapts based on performance and level

### 🗺️ Concept Maps
- Visual representation of skill topic relationships
- Programmatically generated using NetworkX
- Shows beginner → intermediate → advanced progression

### 📚 Gemini-Powered Resource Recommendations
- **Gemini generates personalized recommendations** from:
  - **YouTube**: Free video tutorials with timestamps
  - **Coursera**: University courses (free audit / paid certificates)
  - **Udemy**: Marketplace courses (185,000+ in 75+ languages)

### 🔒 Data Privacy
- No sensitive personal data collected
- User data deletion support
- Transparent AI classification explanation

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- Gemini API key (optional for testing with mocks)

### Installation

```bash
cd "HACKAI 26"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```bash
# Required for production
GEMINI_API_KEY=your_gemini_api_key_here

# Optional settings
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./learning_system.db
SESSION_EXPIRY_HOURS=24
```

**Get your Gemini API key**: https://makersuite.google.com/app/apikey

### Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access: http://localhost:8000/docs

## Gemini Integration

### Overview

The system uses Google's Gemini API for three critical functions:

1. **Classification**: Questionnaire responses → Skill level
2. **Recommendations**: Learner profile → Course suggestions
3. **Quiz Scoring**: Free-form answers → Detailed feedback

### Configuration

```python
# In .env file
GEMINI_API_KEY=your_key_here
```

### Prompt Structure

#### Classification Prompt
```
You are an expert educational assessor. Based on the questionnaire responses,
classify the learner's skill level using the Dreyfus Model:
- BEGINNER (Novice/Advanced Beginner)
- INTERMEDIATE (Competent)  
- ADVANCED (Proficient/Expert)

Respond with JSON: {"level": "...", "confidence": 0.0-1.0, "reasoning": [...]}
```

#### Recommendation Prompt
```
Recommend 2-3 courses from YouTube, Coursera, or Udemy for [skill] at [level] level.
Include: title, platform, url, difficulty, duration, price, rating.
For YouTube, include start/end timestamps for specific segments.
```

### Mock Responses (Testing Without API Key)

The system includes a `MockGeminiClient` for testing:

```python
from app.services.gemini_client import MockGeminiClient, set_client

# Set up mock for testing
mock_client = MockGeminiClient()
set_client(mock_client)

# All Gemini calls now return deterministic mock responses
```

## API Endpoints

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/start` | Start learning session |
| GET | `/api/v1/sessions/{session_id}` | Get session status |

### Questionnaire (Gemini Classification)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/questionnaire/submit` | Submit & classify via Gemini |
| GET | `/api/v1/questionnaire/classification-explanation` | How Gemini classifies |

### Quiz
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/quiz/{session_id}` | Get diagnostic quiz |
| POST | `/api/v1/quiz/submit` | Submit (Gemini scores text answers) |

### Practice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/practice/{session_id}/start` | Start scenario |
| POST | `/api/v1/practice/action` | Take action |

### Resources (Gemini Recommendations)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/resources/{session_id}` | Get Gemini recommendations |
| GET | `/api/v1/resources/platforms/info` | Platform details |

### Privacy
| Method | Endpoint | Description |
|--------|----------|-------------|
| DELETE | `/api/v1/privacy/data` | Delete user data |
| POST | `/api/v1/privacy/challenge-level` | Challenge assessment |

## Testing with Mocked Gemini

Run the full test suite **without an API key**:

```bash
# Generate synthetic profiles and test with mocked Gemini
python -m scripts.seed_data --count 100 --validate
```

Output:
```
SEED DATA GENERATOR WITH MOCKED GEMINI RESPONSES
================================================
This script tests the learning system WITHOUT requiring a Gemini API key.

Generating 100 synthetic learner profiles...

CLASSIFICATION VALIDATION (with Mocked Gemini)
==============================================
Accuracy: 100.0%
Gemini API calls made (mocked): 100

RECOMMENDATION VALIDATION (with Mocked Gemini)
==============================================
Profiles with recommendations: 20
Platform distribution:
  youtube: 20
  coursera: 20
  udemy: 20
```

### Mock Response Files

After running seed_data.py:
- `scripts/seed_data.json` - Synthetic profiles
- `scripts/mock_gemini_responses.json` - Mock response templates

## Adding New Skills

1. Create skill config in `app/data/skills/`:

```json
{
  "skill_id": "javascript",
  "skill_name": "JavaScript",
  "sub_skills": [...],
  "quiz_questions": {
    "beginner": [...],
    "intermediate": [...],
    "advanced": [...]
  },
  "scenarios": [...],
  "concept_map": {...}
}
```

2. Gemini automatically handles:
   - Classification for any skill
   - Recommendations from YouTube/Coursera/Udemy

## Extending to New Providers

The system is modular. To add new resource platforms:

1. Update `Platform` enum in `app/models/schemas.py`
2. Modify Gemini prompt in `gemini_client.py` to include new platform
3. Add platform handling in `recommendations.py`

## Project Structure

```
HACKAI 26/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models/
│   │   ├── schemas.py       # Pydantic models
│   │   └── database.py      # SQLAlchemy models
│   ├── routers/             # API endpoints
│   ├── services/
│   │   ├── gemini_client.py # Gemini API + Mock client
│   │   ├── classification.py # Uses Gemini
│   │   ├── recommendations.py # Uses Gemini
│   │   ├── quiz_generator.py # Uses Gemini for text answers
│   │   └── ...
│   └── data/
│       └── skills/          # Skill configurations
├── tests/test_api.py
├── scripts/
│   └── seed_data.py         # Mock Gemini testing
├── requirements.txt
└── README.md
```

## Technical Notes

### Classification Flow
```
User Answers → Format for Gemini → Gemini API → Parse Response → Store Level
```
No local threshold logic - Gemini's classification is used directly.

### Recommendation Flow
```
Level + Preferences → Build Prompt → Gemini API → Parse JSON → Filter → Return
```
Gemini generates actual course recommendations from YouTube/Coursera/Udemy.

### Platform Details

| Platform | Pricing | Notes |
|----------|---------|-------|
| YouTube | Free | Timestamps for specific segments |
| Coursera | $49+/mo | Free audit available |
| Udemy | $12-200 | Frequent sales |

## License

MIT License
