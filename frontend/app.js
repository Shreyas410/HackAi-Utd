// API Configuration
const API_BASE = 'http://localhost:8000/api/v1';

// Application State
let state = {
    sessionId: null,
    skill: null,
    questionnaire: [],
    currentLevel: null,
    quizId: null,
    quizQuestions: []
};

// Utility Functions
function showLoading(text = 'Processing...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

function showStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.step-content').forEach(el => {
        el.classList.remove('active');
    });
    
    // Show target step
    document.getElementById(`step-${stepNumber}`).classList.add('active');
    
    // Update progress bar
    document.querySelectorAll('.progress-bar .step').forEach((el, index) => {
        el.classList.remove('active', 'completed');
        if (index + 1 < stepNumber) {
            el.classList.add('completed');
        } else if (index + 1 === stepNumber) {
            el.classList.add('active');
        }
    });
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Step 1: Start Session
async function startSession() {
    const name = document.getElementById('learner-name').value.trim();
    const skill = document.getElementById('skill-input').value.trim();
    
    if (!skill) {
        alert('Please enter a skill you want to learn.');
        return;
    }
    
    showLoading('Starting your learning session...');
    
    try {
        const response = await apiCall('/sessions/start', {
            method: 'POST',
            body: JSON.stringify({
                skill: skill,
                learner_name: name || 'Learner'
            })
        });
        
        state.sessionId = response.session_id;
        state.skill = skill;
        state.questionnaire = response.questionnaire;
        
        renderQuestionnaire();
        hideLoading();
        showStep(2);
        
    } catch (error) {
        hideLoading();
        alert('Failed to start session: ' + error.message);
    }
}

// Step 2: Questionnaire
function renderQuestionnaire() {
    const container = document.getElementById('questionnaire-container');
    
    // Filter to show only required questions and key optional ones
    const importantQuestions = state.questionnaire.filter(q => 
        q.required || 
        q.question_id.includes('self_rating') || 
        q.question_id === 'prior_exposure' ||
        q.question_id === 'learning_goal'
    ).slice(0, 8); // Limit to 8 questions for better UX
    
    container.innerHTML = importantQuestions.map((q, index) => `
        <div class="question-item" data-question-id="${q.question_id}">
            <div class="question-text">${index + 1}. ${q.prompt}</div>
            <div class="options">
                ${q.options.map(opt => `
                    <label class="option-label">
                        <input type="radio" name="q_${q.question_id}" value="${opt.value}">
                        <span>${opt.label}</span>
                    </label>
                `).join('')}
            </div>
        </div>
    `).join('');
}

async function submitQuestionnaire() {
    const answers = [];
    const questions = document.querySelectorAll('.question-item');
    
    questions.forEach(q => {
        const questionId = q.dataset.questionId;
        const selected = q.querySelector('input:checked');
        if (selected) {
            answers.push({
                question_id: questionId,
                answer: selected.value
            });
        }
    });
    
    if (answers.length < 3) {
        alert('Please answer at least 3 questions.');
        return;
    }
    
    showLoading('Analyzing your responses with AI...');
    
    try {
        const response = await apiCall('/questionnaire/submit', {
            method: 'POST',
            body: JSON.stringify({
                session_id: state.sessionId,
                answers: answers
            })
        });
        
        state.currentLevel = response.assigned_level;
        renderClassificationResults(response);
        hideLoading();
        showStep(3);
        
    } catch (error) {
        hideLoading();
        alert('Failed to submit questionnaire: ' + error.message);
    }
}

// Step 3: Classification Results
function renderClassificationResults(response) {
    const levelBadge = document.getElementById('level-badge');
    const levelText = document.getElementById('assigned-level');
    const confidenceValue = document.getElementById('confidence-value');
    const confidenceFill = document.getElementById('confidence-fill');
    const factorsList = document.getElementById('factors-list');
    
    // Update level badge
    levelBadge.className = 'level-badge ' + response.assigned_level;
    levelText.textContent = response.assigned_level.charAt(0).toUpperCase() + response.assigned_level.slice(1);
    
    // Update confidence
    const confidence = Math.round(response.explanation.confidence * 100);
    confidenceValue.textContent = confidence + '%';
    confidenceFill.style.width = confidence + '%';
    
    // Update factors
    factorsList.innerHTML = response.explanation.factors.map(factor => 
        `<li>${factor}</li>`
    ).join('');
}

// Step 4: Quiz
async function startQuiz() {
    showLoading('Generating your personalized quiz...');
    
    try {
        const response = await apiCall(`/quiz/${state.sessionId}?num_questions=5`);
        
        state.quizId = response.quiz_id;
        state.quizQuestions = response.questions;
        
        renderQuiz(response.questions);
        hideLoading();
        showStep(4);
        
    } catch (error) {
        hideLoading();
        alert('Failed to load quiz: ' + error.message);
    }
}

function renderQuiz(questions) {
    const container = document.getElementById('quiz-container');
    
    container.innerHTML = questions.map((q, index) => `
        <div class="quiz-question" data-question-id="${q.question_id}">
            <span class="question-number">Question ${index + 1}</span>
            <div class="question-text">${q.prompt || q.question}</div>
            <div class="options">
                ${q.options.map(opt => `
                    <label class="option-label">
                        <input type="radio" name="quiz_${q.question_id}" value="${opt.value}">
                        <span>${opt.label}</span>
                    </label>
                `).join('')}
            </div>
        </div>
    `).join('');
}

async function submitQuiz() {
    const answers = [];
    const questions = document.querySelectorAll('.quiz-question');
    
    questions.forEach(q => {
        const questionId = q.dataset.questionId;
        const selected = q.querySelector('input:checked');
        if (selected) {
            answers.push({
                question_id: questionId,
                answer: selected.value
            });
        }
    });
    
    if (answers.length < state.quizQuestions.length) {
        alert('Please answer all questions.');
        return;
    }
    
    showLoading('Scoring your quiz...');
    
    try {
        const response = await apiCall('/quiz/submit', {
            method: 'POST',
            body: JSON.stringify({
                session_id: state.sessionId,
                quiz_id: state.quizId,
                answers: answers
            })
        });
        
        // Show quiz results
        document.getElementById('quiz-results').classList.remove('hidden');
        const score = response.score_percentage || response.score || 0;
        document.getElementById('quiz-score').textContent = Math.round(score) + '%';
        
        // Display skill score (1-10)
        const skillScore = response.skill_score || Math.ceil((score / 100) * 10) || 1;
        document.getElementById('skill-score').textContent = skillScore;
        
        // Display feedback
        const feedbackEl = document.getElementById('quiz-feedback');
        if (response.feedback) {
            feedbackEl.textContent = response.feedback;
            feedbackEl.classList.remove('hidden');
        }
        
        // Update level if changed
        if (response.new_level) {
            state.currentLevel = response.new_level;
        }
        
        // Load recommendations
        await loadRecommendations();
        hideLoading();
        showStep(5);
        
    } catch (error) {
        hideLoading();
        alert('Failed to submit quiz: ' + error.message);
    }
}

// Step 5: Recommendations
async function loadRecommendations() {
    try {
        // Request more recommendations (limit=6)
        const response = await apiCall(`/resources/${state.sessionId}/recommendations?limit=6`);
        renderRecommendations(response.recommendations, response.meta);
    } catch (error) {
        console.error('Failed to load recommendations:', error);
        // Show placeholder recommendations
        renderPlaceholderRecommendations();
    }
}

function renderRecommendations(recommendations, meta) {
    const container = document.getElementById('recommendations-list');
    
    if (!recommendations || recommendations.length === 0) {
        renderPlaceholderRecommendations();
        return;
    }
    
    // Show pipeline metadata for debugging
    if (meta) {
        console.log('Recommendation pipeline:', meta);
        console.log(`YouTube API: ${meta.youtube_api_used ? 'Yes' : 'No'}`);
        console.log(`Direct links: ${meta.direct_count || 0}, Search links: ${meta.search_count || 0}`);
    }
    
    container.innerHTML = recommendations.map(rec => {
        const platform = (rec.platform || 'unknown').toLowerCase();
        const duration = rec.duration_hours || rec.duration || null;
        const title = rec.title || 'Recommended Course';
        const description = rec.description || '';
        const reason = rec.why_recommended || rec.reason || description || '';
        const rating = rec.rating ? rec.rating.toFixed(1) : null;
        const isFree = rec.is_free !== false && platform === 'youtube' ? true : rec.is_free;
        const price = isFree ? '🆓 Free' : '💰 ' + (rec.price || 'Paid');
        const url = rec.url || '#';
        const difficulty = rec.difficulty || state.currentLevel || 'beginner';
        const urlType = rec.url_type || 'direct';
        const source = rec.source || '';
        
        // Build meta info
        let metaItems = [];
        if (duration) metaItems.push(`<span>⏱️ ${duration}h</span>`);
        metaItems.push(`<span>${price}</span>`);
        if (rating) metaItems.push(`<span>⭐ ${rating}</span>`);
        
        // URL type badge - YouTube API verified is best, then direct, then search
        let urlTypeBadge;
        if (source === 'youtube_api') {
            urlTypeBadge = '<span class="url-type-badge verified">✓ Verified</span>';
        } else if (urlType === 'direct') {
            urlTypeBadge = '<span class="url-type-badge direct">📚 Course</span>';
        } else {
            urlTypeBadge = '<span class="url-type-badge search">🔍 Search</span>';
        }
        
        // Link text based on URL type
        const linkText = urlType === 'direct' ? 'Open Course →' : 'View Search Results →';
        
        // Card class - verified links get special styling
        const cardClass = source === 'youtube_api' ? 'verified-link' : 
                         (urlType === 'direct' ? 'direct-link' : 'search-link');
        
        return `
            <div class="recommendation-card ${cardClass}">
                <div class="card-header">
                    <span class="platform-badge ${platform}">${platform}</span>
                    <span class="difficulty-badge ${difficulty}">${difficulty}</span>
                    ${urlTypeBadge}
                </div>
                <h4>${escapeHtml(title)}</h4>
                <div class="meta">
                    ${metaItems.join('')}
                </div>
                ${reason ? `<p class="reason">${escapeHtml(reason)}</p>` : ''}
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="view-link">${linkText}</a>
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderPlaceholderRecommendations() {
    const container = document.getElementById('recommendations-list');
    const level = state.currentLevel || 'beginner';
    
    const placeholders = {
        beginner: [
            { platform: 'youtube', title: 'Python for Beginners - Full Course', duration: 4.5, free: true },
            { platform: 'coursera', title: 'Python Fundamentals Specialization', duration: 40, free: false },
            { platform: 'udemy', title: 'Complete Python Bootcamp', duration: 22, free: false }
        ],
        intermediate: [
            { platform: 'youtube', title: 'Intermediate Python Projects', duration: 6, free: true },
            { platform: 'coursera', title: 'Python Data Structures', duration: 30, free: false },
            { platform: 'udemy', title: 'Python OOP Deep Dive', duration: 15, free: false }
        ],
        advanced: [
            { platform: 'youtube', title: 'Advanced Python Techniques', duration: 3, free: true },
            { platform: 'udemy', title: 'Python Design Patterns', duration: 12, free: false },
            { platform: 'coursera', title: 'Applied Python Development', duration: 50, free: false }
        ]
    };
    
    const recs = placeholders[level] || placeholders.beginner;
    
    container.innerHTML = recs.map(rec => `
        <div class="recommendation-card">
            <span class="platform-badge ${rec.platform}">${rec.platform}</span>
            <h4>${rec.title}</h4>
            <div class="meta">
                <span>⏱️ ${rec.duration}h</span>
                <span>${rec.free ? '🆓 Free' : '💰 Paid'}</span>
            </div>
            <p class="reason">Recommended for ${level} level learners</p>
        </div>
    `).join('');
}

// Concept Map
async function showConceptMap() {
    showLoading('Loading concept map...');
    
    try {
        const skillEncoded = encodeURIComponent(state.skill);
        const imageUrl = `${API_BASE}/concept-map/${skillEncoded}/image`;
        
        document.getElementById('concept-map-title').textContent = state.skill;
        document.getElementById('concept-map-image').src = imageUrl;
        document.getElementById('concept-map-modal').classList.remove('hidden');
        
        hideLoading();
    } catch (error) {
        hideLoading();
        alert('Failed to load concept map: ' + error.message);
    }
}

function closeConceptMap() {
    document.getElementById('concept-map-modal').classList.add('hidden');
}

// Start Over
function startOver() {
    state = {
        sessionId: null,
        skill: null,
        questionnaire: [],
        currentLevel: null,
        quizId: null,
        quizQuestions: []
    };
    
    // Reset forms
    document.getElementById('learner-name').value = '';
    document.getElementById('skill-input').value = '';
    document.getElementById('quiz-results').classList.add('hidden');
    
    showStep(1);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Close modal on outside click
    document.getElementById('concept-map-modal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeConceptMap();
        }
    });
    
    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeConceptMap();
        }
    });
    
    console.log('Personalized Learning System loaded');
});
