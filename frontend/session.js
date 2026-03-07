// DOM Elements
const displayTopic = document.getElementById('displayTopic');
const timeDisplay = document.getElementById('timeDisplay');
const timerBadge = document.getElementById('timerBadge');
const courseContent = document.getElementById('courseContent');
const chatHistory = document.getElementById('chatHistory');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingText = document.getElementById('loadingText');

const timesUpModal = document.getElementById('timesUpModal');
const timesUpOverlay = document.getElementById('timesUpOverlay');
const continueBtn = document.getElementById('continueBtn');
const takeQuizBtn = document.getElementById('takeQuizBtn');
const endSessionBtn = document.getElementById('endSessionBtn');

const quizOverlay = document.getElementById('quizOverlay');
const quizForm = document.getElementById('quizForm');
const quizQuestionsContainer = document.getElementById('quizQuestionsContainer');
const reportOverlay = document.getElementById('reportOverlay');

// Session State
let topic = sessionStorage.getItem('qlTopic') || 'General Knowledge';
let timeLimitStr = sessionStorage.getItem('qlTime') || '5';
let timeLimitMinutes = parseInt(timeLimitStr);
let timeRemainingSeconds = timeLimitMinutes * 60;
let timerInterval;

let rawContent = "";
let chatContextHistory = [];
let quizDataState = [];

// Initialize Page
window.addEventListener('load', async () => {
    // Check if user is logged in
    const token = localStorage.getItem('authToken');
    if (!token) {
        alert("Authentication required. Please log in.");
        window.location.href = 'index.html';
        return;
    }

    displayTopic.textContent = topic;
    updateTimerDisplay();

    // Fetch initial content
    await startSession();
});

// Timer Logic
function updateTimerDisplay() {
    const min = Math.floor(timeRemainingSeconds / 60);
    const sec = timeRemainingSeconds % 60;
    timeDisplay.textContent = `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;

    if (timeRemainingSeconds <= 60 && timeRemainingSeconds > 0) {
        timerBadge.classList.add('warning');
    } else {
        timerBadge.classList.remove('warning');
    }
}

function startTimer() {
    timerInterval = setInterval(() => {
        timeRemainingSeconds--;
        updateTimerDisplay();

        if (timeRemainingSeconds <= 0) {
            clearInterval(timerInterval);
            timeDisplay.textContent = "00:00";
            showTimesUpModal();
        }
    }, 1000);
}

// API Interactions
async function startSession() {
    loadingOverlay.style.display = 'flex';

    try {
        const response = await fetch('/api/quick-learn/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, time_limit_minutes: timeLimitMinutes })
        });

        const data = await response.json();

        if (response.ok) {
            rawContent = data.content;
            // Parse Markdown
            courseContent.innerHTML = marked.parse(rawContent);
            startTimer();
        } else {
            courseContent.innerHTML = `<p style="color:red">Failed to load content: ${data.detail}</p>`;
        }
    } catch (error) {
        courseContent.innerHTML = `<p style="color:red">An error occurred while connecting to the server.</p>`;
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

// Chat Functionality
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;

    // Add user message to UI
    appendChatMessage('user', question);
    chatInput.value = '';

    // Keep history lean (last 5 messages)
    const recentHistory = chatContextHistory.slice(-5);

    // Add AI loading indicator
    const loadingId = 'loading-' + Date.now();
    appendChatMessage('ai', '<span class="loader-dots">Thinking...</span>', loadingId);

    try {
        const response = await fetch('/api/quick-learn/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                content: rawContent,
                question: question,
                history: recentHistory
            })
        });

        const data = await response.json();
        if (response.ok) {
            // Remove loading msg and append real answer
            document.getElementById(loadingId).remove();
            appendChatMessage('ai', marked.parse(data.answer));

            // Save to history state
            chatContextHistory.push({ user: question, ai: data.answer });
        }
    } catch (error) {
        document.getElementById(loadingId).remove();
        appendChatMessage('ai', "Sorry, I can't reach the server right now.");
    }
});

function appendChatMessage(sender, textHTML, forceId = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${sender}`;
    if (forceId) msgDiv.id = forceId;
    msgDiv.innerHTML = textHTML;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight; // Auto-scroll
}

// Time's Up Flow
function showTimesUpModal() {
    timesUpModal.classList.add('show');
    timesUpOverlay.classList.add('show');
}

function hideTimesUpModal() {
    timesUpModal.classList.remove('show');
    timesUpOverlay.classList.remove('show');
}

continueBtn.addEventListener('click', () => {
    hideTimesUpModal();
    endSessionBtn.style.display = 'inline-block'; // Show manual end button
});

takeQuizBtn.addEventListener('click', () => {
    hideTimesUpModal();
    initiateQuiz();
});

endSessionBtn.addEventListener('click', () => {
    initiateQuiz();
});

// Quiz Flow
async function initiateQuiz() {
    loadingText.textContent = "Generating your personalized quiz...";
    loadingOverlay.style.display = 'flex';

    try {
        const response = await fetch('/api/quick-learn/quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                content: rawContent,
                history: chatContextHistory.slice(-5)
            })
        });

        const data = await response.json();
        if (response.ok) {
            quizDataState = data.quiz;
            renderQuizForm(quizDataState);
            quizOverlay.style.display = 'flex';
        } else {
            alert('Failed to generate quiz.');
        }
    } catch (error) {
        alert('Error connecting to the quiz generator.');
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

function renderQuizForm(quizArray) {
    quizQuestionsContainer.innerHTML = '';

    quizArray.forEach((q, index) => {
        const qCard = document.createElement('div');
        qCard.className = 'question-card';

        let html = `<h3>Question ${index + 1}</h3><p>${q.question}</p>`;
        html += `<ul class="options-list">`;

        q.options.forEach((opt, optIdx) => {
            // Clean value just in case
            const optValue = opt.replace(/"/g, '&quot;');
            html += `
                <li>
                    <label>
                        <input type="radio" name="q_${q.id}" value="${optValue}" required>
                        <span>${optValue}</span>
                    </label>
                </li>
            `;
        });
        html += `</ul>`;
        qCard.innerHTML = html;
        quizQuestionsContainer.appendChild(qCard);
    });
}

// Quiz Submission
quizForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(quizForm);
    const userAnswers = {};

    // Map form data back to question IDs
    for (let [key, value] of formData.entries()) {
        const qId = key.split('_')[1];
        userAnswers[qId] = value;
    }

    loadingText.textContent = "Evaluating your answers...";
    loadingOverlay.style.display = 'flex';
    quizOverlay.style.display = 'none';

    try {
        const response = await fetch('/api/quick-learn/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_answers: userAnswers,
                quiz_data: quizDataState
            })
        });

        const data = await response.json();
        if (response.ok) {
            showReport(data.report);
        } else {
            alert('Failed to evaluate quiz.');
            quizOverlay.style.display = 'flex';
        }
    } catch (error) {
        alert('Error communicating with server.');
        quizOverlay.style.display = 'flex';
    } finally {
        loadingOverlay.style.display = 'none';
    }
});

function showReport(report) {
    reportOverlay.style.display = 'flex';

    document.getElementById('reportScore').textContent = report.score;

    const strongList = document.getElementById('strongTopicsList');
    strongList.innerHTML = '';
    report.strong_topics.forEach(t => {
        const li = document.createElement('li');
        li.textContent = t;
        strongList.appendChild(li);
    });

    const focusList = document.getElementById('focusTopicsList');
    focusList.innerHTML = '';
    report.focus_topics.forEach(t => {
        const li = document.createElement('li');
        li.textContent = t;
        focusList.appendChild(li);
    });
}
