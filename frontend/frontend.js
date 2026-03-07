/* ============================================
   DOM ELEMENTS
   ============================================ */
const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');
const navLinks = document.querySelectorAll('.nav-link');
const loginBtn = document.getElementById('loginBtn');
const loginModal = document.getElementById('loginModal');
const closeLogin = document.getElementById('closeLogin');
const modalOverlay = document.getElementById('modalOverlay');
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const showSignup = document.getElementById('showSignup');
const showLogin = document.getElementById('showLogin');
const modalTitle = document.getElementById('modalTitle');
const signupError = document.getElementById('signupError');
const quickLearnModal = document.getElementById('quickLearnModal');
const closeQuickLearn = document.getElementById('closeQuickLearn');
const quickLearnForm = document.getElementById('quickLearnForm');
const scrollToCategories = document.getElementById('scrollToCategories');
const ctaButton = document.getElementById('ctaButton');

/* ============================================
   NAVIGATION FUNCTIONALITY
   ============================================ */
// Hamburger menu toggle
hamburger.addEventListener('click', () => {
    navMenu.classList.toggle('active');
});

// Close menu when a link is clicked
navLinks.forEach(link => {
    link.addEventListener('click', () => {
        navMenu.classList.remove('active');
    });
});

// Sticky navbar on scroll
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 100) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

/* ============================================
   MODAL FUNCTIONALITY
   ============================================ */
// Open login modal
loginBtn.addEventListener('click', openLoginModal);
ctaButton.addEventListener('click', openLoginModal);

function openLoginModal() {
    loginModal.classList.add('show');
    modalOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
    switchToLogin(); // Reset view to login when opened
}

function closeLoginModal() {
    loginModal.classList.remove('show');
    modalOverlay.classList.remove('show');
    document.body.style.overflow = 'auto';
}

function switchToLogin() {
    signupForm.style.display = 'none';
    loginForm.style.display = 'block';
    modalTitle.textContent = 'Login to LearnPath';
    signupError.style.display = 'none';
}

// Toggle between Login and Sign Up views
showSignup.addEventListener('click', (e) => {
    e.preventDefault();
    loginForm.style.display = 'none';
    signupForm.style.display = 'block';
    modalTitle.textContent = 'Create an Account';
    signupError.style.display = 'none';
});

showLogin.addEventListener('click', (e) => {
    e.preventDefault();
    switchToLogin();
});

// Close modal when X is clicked
closeLogin.addEventListener('click', closeLoginModal);
closeQuickLearn.addEventListener('click', closeQuickLearnModal);

// Close modal when overlay is clicked
modalOverlay.addEventListener('click', () => {
    closeLoginModal();
    closeQuickLearnModal();
});

// Prevent modal from closing when clicking inside it
loginModal.addEventListener('click', (e) => {
    e.stopPropagation();
});
quickLearnModal.addEventListener('click', (e) => {
    e.stopPropagation();
});

function openQuickLearnModal() {
    quickLearnModal.classList.add('show');
    modalOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeQuickLearnModal() {
    quickLearnModal.classList.remove('show');
    // Only remove overlay if login isn't open
    if (!loginModal.classList.contains('show')) {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

/* ============================================
   FORM HANDLING
   ============================================ */
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const remember = document.getElementById('remember').checked;

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Login successful!');
            storeAuthToken(data.token);
            closeLoginModal();
            loginForm.reset();
        } else {
            alert('Login failed: ' + (data.detail || 'Unknown error.'));
        }
    } catch (error) {
        console.error('Error logging in:', error);
        alert('An error occurred during login. Please try again.');
    }
});

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
        signupError.textContent = "Passwords do not match.";
        signupError.style.display = 'block';
        return;
    }

    signupError.style.display = 'none';

    try {
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Account created successfully! You can now sign in.');
            signupForm.reset();
            switchToLogin();
        } else {
            signupError.textContent = data.detail || 'Failed to create account.';
            signupError.style.display = 'block';
        }
    } catch (error) {
        console.error('Error signing up:', error);
        signupError.textContent = 'An error occurred during sign up. Please try again.';
        signupError.style.display = 'block';
    }
});

/* ============================================
   SCROLL TO SECTIONS
   ============================================ */
scrollToCategories.addEventListener('click', () => {
    document.getElementById('categories').scrollIntoView({ behavior: 'smooth' });
});

/* ============================================
   CATEGORY NAVIGATION
   ============================================ */
function navigateToFullTime() {
    if (!isUserLoggedIn()) {
        alert("Please log in first to access the learning path.");
        openLoginModal();
        return;
    }
    alert('Navigating to Full-Time Questionnaire...\n\nThis would open the detailed questionnaire form.');
    console.log('Navigating to: /analysis (Full Time Learning Path)');
}

function navigateToQuickLearn() {
    if (!isUserLoggedIn()) {
        alert("Please log in first to access the quick learner module.");
        openLoginModal();
        return;
    }
    // Open the setup modal instead of navigating blindly
    openQuickLearnModal();
}

quickLearnForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const topic = document.getElementById('qlTopic').value;
    const timeLimit = document.getElementById('qlTime').value;

    // Store configuration in session storage so session.html can use it
    sessionStorage.setItem('qlTopic', topic);
    sessionStorage.setItem('qlTime', timeLimit);

    // Redirect to the learning session page
    window.location.href = 'session.html';
});

/* ============================================
   INTERACTIVE ELEMENTS
   ============================================ */
// Add animation to cards on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe category cards, feature cards, and timeline items
document.querySelectorAll('.category-card, .feature-card, .timeline-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'all 0.6s ease-out';
    observer.observe(el);
});

/* ============================================
   SMOOTH SCROLL BEHAVIOR
   ============================================ */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
        const href = anchor.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const element = document.querySelector(href);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
});

/* ============================================
   HOVER EFFECTS
   ============================================ */
const categoryCards = document.querySelectorAll('.category-card');
categoryCards.forEach(card => {
    card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-10px)';
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0)';
    });
});

/* ============================================
   UTILITY FUNCTIONS
   ============================================ */
// Add active state to navigation links based on scroll position
function updateActiveNavLink() {
    const sections = document.querySelectorAll('section');
    let current = '';

    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        if (scrollY >= sectionTop - 200) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href').slice(1) === current) {
            link.classList.add('active');
        }
    });
}

window.addEventListener('scroll', updateActiveNavLink);

/* ============================================
   PAGE LOAD ANIMATION
   ============================================ */
window.addEventListener('load', () => {
    console.log('LearnPath Frontend Loaded Successfully!');
    console.log('Available routes:');
    console.log('- Full Time Learning: /analysis');
    console.log('- Quick Learning: /multipleAnalysis');
});

/* ============================================
   HELPER FUNCTIONS FOR FUTURE IMPLEMENTATION
   ============================================ */

/**
 * Submit full-time questionnaire
 * @param {FormData} formData - Questionnaire answers
 */
async function submitFullTimeQuestionnaire(formData) {
    try {
        const response = await fetch('/analysis', {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            console.log('Questionnaire submitted successfully');
        }
    } catch (error) {
        console.error('Error submitting questionnaire:', error);
    }
}

/**
 * Submit quick learning request
 * @param {string} topic - Learning topic
 * @param {number} timeMinutes - Available time in minutes
 */
async function submitQuickLearnRequest(topic, timeMinutes) {
    try {
        const response = await fetch('/multipleAnalysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ topic, timeMinutes })
        });
        if (response.ok) {
            console.log('Quick learning request submitted');
        }
    } catch (error) {
        console.error('Error submitting quick learn request:', error);
    }
}

/**
 * Check if user is logged in
 */
function isUserLoggedIn() {
    const token = localStorage.getItem('authToken');
    return !!token;
}

/**
 * Store authentication token
 * @param {string} token - JWT token from backend
 */
function storeAuthToken(token) {
    localStorage.setItem('authToken', token);
}

/**
 * Log out user
 */
function logoutUser() {
    localStorage.removeItem('authToken');
    closeLoginModal();
    console.log('User logged out');
}

/* ============================================
   KEYBOARD SHORTCUTS
   ============================================ */
document.addEventListener('keydown', (e) => {
    // ESC to close modal
    if (e.key === 'Escape') {
        closeLoginModal();
        closeQuickLearnModal();
    }
    // Alt+Q for quick learn
    if (e.altKey && e.key === 'q') {
        navigateToQuickLearn();
    }
    // Alt+F for full time
    if (e.altKey && e.key === 'f') {
        navigateToFullTime();
    }
});

/* ============================================
   EXPORT FUNCTIONS FOR EXTERNAL USE
   ============================================ */
window.LearnPath = {
    openLoginModal,
    closeLoginModal,
    navigateToFullTime,
    navigateToQuickLearn,
    submitFullTimeQuestionnaire,
    submitQuickLearnRequest,
    isUserLoggedIn,
    storeAuthToken,
    logoutUser
};
