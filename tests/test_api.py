"""
API tests for the Personalised Learning System.
Uses mocked Gemini responses for all tests.

Run with: pytest tests/test_api.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
import json

from app.main import app
from app.models.database import init_db, engine, Base
from app.services.gemini_client import MockGeminiClient, set_client


@pytest.fixture(autouse=True)
def setup_mock_gemini():
    """Set up mock Gemini client for all tests."""
    mock_client = MockGeminiClient()
    set_client(mock_client)
    yield
    # Reset after tests if needed


@pytest.fixture
async def client():
    """Create test client with fresh database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_questionnaire_responses():
    """Sample questionnaire responses for testing."""
    return {
        "answers": [
            {"question_id": "job_title", "answer": "Software Developer"},
            {"question_id": "experience_years", "answer": "5"},
            {"question_id": "prior_exposure", "answer": "professional"},
            {"question_id": "learning_reason", "answer": ["career", "project"]},
            {"question_id": "desired_outcome", "answer": "proficient"},
            {"question_id": "self_rating_basic_syntax", "answer": "4"},
            {"question_id": "self_rating_control_flow", "answer": "4"},
            {"question_id": "self_rating_data_structures", "answer": "3"},
            {"question_id": "self_rating_functions", "answer": "4"},
            {"question_id": "self_rating_modules", "answer": "3"},
            {"question_id": "self_rating_file_io", "answer": "3"},
            {"question_id": "self_rating_oop", "answer": "3"},
            {"question_id": "preferred_modalities", "answer": ["video", "interactive_exercises"]},
            {"question_id": "time_availability", "answer": "10"}
        ]
    }


class TestHealthAndRoot:
    """Test basic endpoints."""
    
    @pytest.mark.asyncio
    async def test_root(self, client):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data
    
    @pytest.mark.asyncio
    async def test_health(self, client):
        """Test health endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_list_skills(self, client):
        """Test skills listing endpoint."""
        response = await client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data


class TestSessionManagement:
    """Test session creation and management."""
    
    @pytest.mark.asyncio
    async def test_start_session(self, client):
        """Test starting a new learning session."""
        response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert data["skill"] == "Python programming"
        assert "questionnaire" in data
        assert len(data["questionnaire"]) > 0
    
    @pytest.mark.asyncio
    async def test_questionnaire_structure(self, client):
        """Test questionnaire has correct structure."""
        response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        data = response.json()
        
        questionnaire = data["questionnaire"]
        for question in questionnaire:
            assert "question_id" in question
            assert "type" in question
            assert "prompt" in question
        
        categories = {q.get("category") for q in questionnaire}
        assert "background" in categories
        assert "self_assessment" in categories


class TestQuestionnaireWithGemini:
    """Test questionnaire submission with Gemini classification."""
    
    @pytest.mark.asyncio
    async def test_submit_questionnaire_uses_gemini(self, client, sample_questionnaire_responses):
        """Test that questionnaire submission uses Gemini for classification."""
        # Create session
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        # Submit questionnaire
        submit_data = {
            "session_id": session_id,
            **sample_questionnaire_responses
        }
        response = await client.post(
            "/api/v1/questionnaire/submit",
            json=submit_data
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert "assigned_level" in data
        assert data["assigned_level"] in ["beginner", "intermediate", "advanced"]
        
        # Check explanation mentions Gemini
        assert "explanation" in data
        assert "factors" in data["explanation"]
        factors_text = " ".join(data["explanation"]["factors"])
        assert "Gemini" in factors_text or "AI" in factors_text
    
    @pytest.mark.asyncio
    async def test_classification_beginner(self, client):
        """Test beginner classification with low ratings."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        # Submit with low ratings (should classify as beginner)
        submit_data = {
            "session_id": session_id,
            "answers": [
                {"question_id": "experience_years", "answer": "0"},
                {"question_id": "prior_exposure", "answer": "none"},
                {"question_id": "self_rating_basic_syntax", "answer": "1"},
                {"question_id": "self_rating_control_flow", "answer": "2"},
                {"question_id": "self_rating_data_structures", "answer": "1"},
            ]
        }
        response = await client.post(
            "/api/v1/questionnaire/submit",
            json=submit_data
        )
        assert response.status_code == 200
        data = response.json()
        
        # Mock Gemini should return beginner for low ratings
        assert data["assigned_level"] == "beginner"
    
    @pytest.mark.asyncio
    async def test_classification_explanation_endpoint(self, client):
        """Test classification explanation endpoint."""
        response = await client.get("/api/v1/questionnaire/classification-explanation")
        assert response.status_code == 200
        data = response.json()
        
        # Should explain Gemini-based classification
        assert "Gemini" in str(data) or "gemini" in str(data).lower()
        assert "levels" in data


class TestQuiz:
    """Test quiz generation and scoring with Gemini."""
    
    @pytest.mark.asyncio
    async def test_get_quiz_after_questionnaire(self, client, sample_questionnaire_responses):
        """Test getting quiz after completing questionnaire."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/quiz/{session_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "quiz_id" in data
        assert "questions" in data
        assert len(data["questions"]) >= 5
    
    @pytest.mark.asyncio
    async def test_submit_quiz(self, client, sample_questionnaire_responses):
        """Test submitting quiz answers."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        quiz_response = await client.get(f"/api/v1/quiz/{session_id}")
        quiz_data = quiz_response.json()
        
        # Submit answers
        answers = [
            {"question_id": q["question_id"], "answer": "a"}
            for q in quiz_data["questions"]
        ]
        
        response = await client.post(
            "/api/v1/quiz/submit",
            json={
                "session_id": session_id,
                "quiz_id": quiz_data["quiz_id"],
                "answers": answers
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "score" in data
        assert "results" in data


class TestResourcesWithGemini:
    """Test resource recommendations via Gemini."""
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, client, sample_questionnaire_responses):
        """Test getting Gemini-generated recommendations."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/resources/{session_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "recommendations" in data
        assert "learner_level" in data
        
        # Check recommendations have expected structure
        if data["recommendations"]:
            rec = data["recommendations"][0]
            assert "title" in rec
            assert "platform" in rec
            assert rec["platform"] in ["youtube", "coursera", "udemy"]
    
    @pytest.mark.asyncio
    async def test_platform_info(self, client):
        """Test platform information endpoint."""
        response = await client.get("/api/v1/resources/platforms/info")
        assert response.status_code == 200
        data = response.json()
        
        assert "platforms" in data
        assert "youtube" in data["platforms"]
        assert "coursera" in data["platforms"]
        assert "udemy" in data["platforms"]


class TestPractice:
    """Test scenario-based practice."""
    
    @pytest.mark.asyncio
    async def test_start_and_play_scenario(self, client, sample_questionnaire_responses):
        """Test starting and taking actions in a scenario."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        # Start scenario
        start_response = await client.post(f"/api/v1/practice/{session_id}/start")
        assert start_response.status_code == 200
        scenario_data = start_response.json()
        
        assert "scenario_id" in scenario_data
        assert "current_node" in scenario_data
        assert "actions" in scenario_data["current_node"]


class TestConceptMap:
    """Test concept map endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_concept_map(self, client):
        """Test getting a concept map."""
        response = await client.get("/api/v1/concept-map/Python%20programming")
        assert response.status_code == 200
        data = response.json()
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0


class TestPrivacy:
    """Test data privacy endpoints."""
    
    @pytest.mark.asyncio
    async def test_data_policy(self, client):
        """Test data policy endpoint."""
        response = await client.get("/api/v1/privacy/data-policy")
        assert response.status_code == 200
        data = response.json()
        
        assert "data_collected" in data
        assert "your_rights" in data
    
    @pytest.mark.asyncio
    async def test_delete_data(self, client, sample_questionnaire_responses):
        """Test data deletion."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python programming"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.request(
            "DELETE",
            "/api/v1/privacy/data",
            json={"session_id": session_id, "confirmation": True}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
