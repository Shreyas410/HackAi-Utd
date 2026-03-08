# Changelog

## [2026-03-07] - Initial Development

### Added
- FastAPI backend with async SQLite database
- Gemini AI integration (gemini-2.5-flash model)
- Mock client for testing without API key
- Frontend SPA with 5-step learning flow
- Skill level classification (Beginner/Intermediate/Advanced)
- Dynamic quiz generation with Gemini
- Quiz scoring with skill_score (1-10 scale)
- Course recommendations from YouTube, Coursera, Udemy
- PROJECT_CONTEXT.md for debugging reference

### Fixed
- Quiz scoring now works (added correct_answer to QuizQuestion schema)
- Quiz displays proper questions (using q.prompt || q.question)
- Recommendations use safe search URLs (no broken links)
- Level-specific recommendations (different content per level)
- NaN% score display fixed in frontend

### Technical Notes
- All recommendation URLs are search URLs (guaranteed to work)
- Gemini model: gemini-2.5-flash
- Fallback: MockGeminiClient when API unavailable
