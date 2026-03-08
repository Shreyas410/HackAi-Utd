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


class TestHybridRecommendations:
    """Test direct-link-first hybrid recommendation pipeline."""
    
    @pytest.mark.asyncio
    async def test_recommendations_have_metadata(self, client, sample_questionnaire_responses):
        """Test that recommendations include pipeline metadata with direct/search counts."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "React"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/resources/{session_id}/recommendations?limit=6")
        assert response.status_code == 200
        data = response.json()
        
        # Check metadata exists with new fields
        assert "meta" in data
        meta = data["meta"]
        assert "skill" in meta
        assert "level" in meta
        assert "direct_count" in meta
        assert "search_count" in meta
        assert "curated_used" in meta
    
    @pytest.mark.asyncio
    async def test_recommendations_have_url_type(self, client, sample_questionnaire_responses):
        """Test that all recommendations have url_type field."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/resources/{session_id}/recommendations?limit=6")
        data = response.json()
        
        for rec in data["recommendations"]:
            assert "url_type" in rec
            assert rec["url_type"] in ["direct", "search"]
            assert "url" in rec
            
            platform = rec["platform"]
            if platform == "youtube":
                assert "youtube.com" in rec["url"]
            elif platform == "coursera":
                assert "coursera.org" in rec["url"]
            elif platform == "udemy":
                assert "udemy.com" in rec["url"]
    
    @pytest.mark.asyncio
    async def test_direct_links_preferred_over_search(self, client, sample_questionnaire_responses):
        """Test that direct links come before search links when available."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Python"}  # Has curated direct links
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/resources/{session_id}/recommendations?limit=6")
        data = response.json()
        
        # Should have at least some direct links for a well-known skill
        meta = data["meta"]
        assert meta["direct_count"] >= 1, "Expected at least one direct course link"
    
    @pytest.mark.asyncio
    async def test_recommendations_platform_diversity(self, client, sample_questionnaire_responses):
        """Test that recommendations include multiple platforms."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "JavaScript"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/resources/{session_id}/recommendations?limit=6")
        data = response.json()
        
        platforms = {rec["platform"] for rec in data["recommendations"]}
        assert len(platforms) >= 2
    
    @pytest.mark.asyncio
    async def test_unknown_skill_uses_fallback(self, client, sample_questionnaire_responses):
        """Test that unknown skills still get recommendations via fallback."""
        create_response = await client.post(
            "/api/v1/sessions/start",
            json={"skill": "Quantum Computing with Qiskit"}
        )
        session_id = create_response.json()["session_id"]
        
        await client.post(
            "/api/v1/questionnaire/submit",
            json={"session_id": session_id, **sample_questionnaire_responses}
        )
        
        response = await client.get(f"/api/v1/resources/{session_id}/recommendations?limit=6")
        assert response.status_code == 200
        data = response.json()
        
        # Should still have recommendations (may be search fallbacks)
        assert len(data["recommendations"]) > 0
        
        # Unknown skills will likely have search fallbacks
        meta = data["meta"]
        assert meta.get("generic_curated_used") or meta.get("search_fallback_used")


class TestCuratedResources:
    """Test curated direct-link resource lookup."""
    
    def test_get_curated_resources_has_direct_urls(self):
        """Test that curated resources have actual direct URLs."""
        from app.data.curated_resources import get_curated_resources
        
        resources = get_curated_resources("Python", "beginner")
        assert len(resources) > 0
        
        for res in resources:
            assert "title" in res
            assert "platform" in res
            assert "url" in res
            assert res["url_type"] == "direct"
            
            # Verify it's a direct URL, not a search URL
            url = res["url"]
            assert "/results?search_query=" not in url
            assert "/search?" not in url
            assert "/courses/search/" not in url
    
    def test_curated_urls_are_valid_direct_links(self):
        """Test that curated URLs are valid direct course/video links."""
        from app.data.curated_resources import get_curated_resources
        
        resources = get_curated_resources("React", "beginner")
        
        for res in resources:
            url = res["url"]
            platform = res["platform"]
            
            if platform == "youtube":
                # Should be a watch or playlist URL
                assert "youtube.com/watch" in url or "youtu.be/" in url or "playlist" in url
            elif platform == "coursera":
                # Should be a learn, specializations, or professional-certificates URL
                assert any(p in url for p in ["/learn/", "/specializations/", "/professional-certificates/"])
            elif platform == "udemy":
                # Should be a course URL
                assert "/course/" in url
    
    def test_get_curated_resources_case_insensitive(self):
        """Test that curated lookup is case insensitive."""
        from app.data.curated_resources import get_curated_resources
        
        res1 = get_curated_resources("python", "beginner")
        res2 = get_curated_resources("PYTHON", "beginner")
        res3 = get_curated_resources("Python", "beginner")
        
        assert len(res1) == len(res2) == len(res3)
    
    def test_generic_fallback_for_unknown_skill(self):
        """Test generic direct resources for unknown skills."""
        from app.data.curated_resources import get_curated_resources, get_generic_direct_resources
        
        # Unknown skill should return empty from curated
        curated = get_curated_resources("Obscure Framework XYZ", "beginner")
        assert len(curated) == 0
        
        # But generic direct resources should still work
        generic = get_generic_direct_resources("beginner")
        assert len(generic) > 0
        
        for res in generic:
            assert "url" in res
            assert res["url_type"] == "direct"


class TestURLBuilding:
    """Test URL building utilities."""
    
    def test_youtube_search_url(self):
        """Test YouTube search URL building."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        url = service._build_youtube_search_url("react tutorial beginner")
        assert "youtube.com/results?search_query=" in url
        assert "react" in url.lower()
    
    def test_coursera_search_url(self):
        """Test Coursera search URL building."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        url = service._build_coursera_search_url("python fundamentals", "beginner")
        assert "coursera.org/search" in url
        assert "python" in url.lower()
    
    def test_udemy_search_url(self):
        """Test Udemy search URL building."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        url = service._build_udemy_search_url("javascript projects", "intermediate")
        assert "udemy.com/courses/search" in url
        assert "javascript" in url.lower()
    
    def test_build_search_fallback_url(self):
        """Test search fallback URL building."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        url = service._build_search_fallback_url(
            platform="youtube",
            query="react tutorial",
            title="React Tutorial",
            skill="React",
            level="beginner"
        )
        
        assert "/results?search_query=" in url
        assert "react" in url.lower()
    
    def test_is_search_url_youtube(self):
        """Test search URL detection for YouTube."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        # Search URLs
        assert service._is_search_url("https://www.youtube.com/results?search_query=react", "youtube")
        
        # Direct URLs - should return False
        assert not service._is_search_url("https://www.youtube.com/watch?v=TlB_eWDSMt4", "youtube")


class TestRecommendationScoring:
    """Test recommendation candidate scoring."""
    
    def test_direct_link_higher_score_than_search(self):
        """Test that direct links score higher than search links."""
        from app.services.recommendations import RecommendationService, RecommendationCandidate
        service = RecommendationService()
        
        direct = RecommendationCandidate(
            title="React Tutorial",
            platform="youtube",
            url="https://www.youtube.com/watch?v=TlB_eWDSMt4",
            url_type="direct",
            source="curated",
            difficulty="beginner"
        )
        
        search = RecommendationCandidate(
            title="React Tutorial",
            platform="youtube",
            url="https://www.youtube.com/results?search_query=react",
            url_type="search",
            source="fallback_search",
            difficulty="beginner"
        )
        
        direct_score = service._score_candidate(direct, "React", "beginner")
        search_score = service._score_candidate(search, "React", "beginner")
        
        assert direct_score > search_score, "Direct links should score higher than search links"
    
    def test_curated_higher_score_than_fallback(self):
        """Test that curated recommendations score higher than fallbacks."""
        from app.services.recommendations import RecommendationService, RecommendationCandidate
        service = RecommendationService()
        
        curated = RecommendationCandidate(
            title="React Tutorial",
            platform="youtube",
            url="https://www.youtube.com/watch?v=TlB_eWDSMt4",
            url_type="direct",
            source="curated",
            difficulty="beginner"
        )
        
        fallback = RecommendationCandidate(
            title="React Tutorial",
            platform="youtube",
            url="https://www.youtube.com/results?search_query=react",
            url_type="search",
            source="fallback_search",
            difficulty="beginner"
        )
        
        curated_score = service._score_candidate(curated, "React", "beginner")
        fallback_score = service._score_candidate(fallback, "React", "beginner")
        
        assert curated_score > fallback_score
    
    def test_level_match_increases_score(self):
        """Test that matching level increases score."""
        from app.services.recommendations import RecommendationService, RecommendationCandidate
        service = RecommendationService()
        
        matching = RecommendationCandidate(
            title="React Tutorial",
            platform="youtube",
            url="https://www.youtube.com/watch?v=TlB_eWDSMt4",
            url_type="direct",
            source="gemini",
            difficulty="beginner"
        )
        
        not_matching = RecommendationCandidate(
            title="React Tutorial",
            platform="youtube",
            url="https://www.youtube.com/watch?v=xyz789",
            url_type="direct",
            source="gemini",
            difficulty="advanced"
        )
        
        matching_score = service._score_candidate(matching, "React", "beginner")
        not_matching_score = service._score_candidate(not_matching, "React", "beginner")
        
        assert matching_score > not_matching_score


class TestURLValidation:
    """Test URL validation for direct vs search detection."""
    
    def test_is_direct_course_url_youtube(self):
        """Test YouTube direct URL detection."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        # Direct URLs (YouTube video IDs are 11 characters)
        assert service._is_direct_course_url("https://www.youtube.com/watch?v=TlB_eWDSMt4", "youtube")
        assert service._is_direct_course_url("https://youtu.be/TlB_eWDSMt4", "youtube")
        assert service._is_direct_course_url("https://www.youtube.com/playlist?list=PLfoo", "youtube")
        
        # Search URLs - should return False
        assert not service._is_direct_course_url("https://www.youtube.com/results?search_query=react", "youtube")
        assert not service._is_direct_course_url("https://www.youtube.com/", "youtube")
    
    def test_is_direct_course_url_coursera(self):
        """Test Coursera direct URL detection."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        assert service._is_direct_course_url("https://www.coursera.org/learn/python", "coursera")
        assert service._is_direct_course_url("https://www.coursera.org/specializations/deep-learning", "coursera")
        
        assert not service._is_direct_course_url("https://www.coursera.org/search?query=python", "coursera")
        assert not service._is_direct_course_url("https://www.coursera.org/", "coursera")
    
    def test_is_direct_course_url_udemy(self):
        """Test Udemy direct URL detection."""
        from app.services.recommendations import RecommendationService
        service = RecommendationService()
        
        assert service._is_direct_course_url("https://www.udemy.com/course/python-bootcamp/", "udemy")
        
        assert not service._is_direct_course_url("https://www.udemy.com/courses/search/?q=python", "udemy")
        assert not service._is_direct_course_url("https://www.udemy.com/", "udemy")


class TestDeduplication:
    """Test recommendation deduplication."""
    
    def test_dedupe_removes_duplicates(self):
        """Test that exact duplicates are removed."""
        from app.services.recommendations import RecommendationService, RecommendationCandidate
        service = RecommendationService()
        
        candidates = [
            RecommendationCandidate(
                title="React Tutorial",
                platform="youtube",
                url="https://www.youtube.com/watch?v=TlB_eWDSMt4",
                url_type="direct",
                source="curated"
            ),
            RecommendationCandidate(
                title="React Tutorial",
                platform="youtube",
                url="https://www.youtube.com/watch?v=TlB_eWDSMt4",
                url_type="direct",
                source="gemini"
            ),
            RecommendationCandidate(
                title="Different Title",
                platform="youtube",
                url="https://www.youtube.com/watch?v=xyz789",
                url_type="direct",
                source="curated"
            )
        ]
        
        deduped = service._dedupe_recommendations(candidates)
        assert len(deduped) == 2
    
    def test_dedupe_keeps_higher_scored_candidates(self):
        """Test that deduplication keeps higher scored candidates."""
        from app.services.recommendations import RecommendationService, RecommendationCandidate
        service = RecommendationService()
        
        high_score = RecommendationCandidate(
            title="React Tutorial Complete",
            platform="youtube",
            url="https://www.youtube.com/watch?v=TlB_eWDSMt4",
            url_type="direct",
            source="curated",
            score=20.0
        )
        
        low_score = RecommendationCandidate(
            title="React Basics Guide",
            platform="youtube",
            url="https://www.youtube.com/watch?v=f2EqECiTBL8",
            url_type="direct",
            source="gemini",
            score=10.0
        )
        
        duplicate = RecommendationCandidate(
            title="React Tutorial Complete",  # Same title as high_score
            platform="youtube",
            url="https://www.youtube.com/watch?v=TlB_eWDSMt4",  # Same URL
            url_type="direct",
            source="gemini",
            score=5.0
        )
        
        candidates = [low_score, duplicate, high_score]
        deduped = service._dedupe_recommendations(candidates)
        
        # Should keep high_score and low_score (unique), remove duplicate
        assert len(deduped) == 2
        # Highest scored should be first
        assert deduped[0].score == 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
