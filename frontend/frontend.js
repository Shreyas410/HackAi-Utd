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
}

function closeLoginModal() {
    loginModal.classList.remove('show');
    modalOverlay.classList.remove('show');
    document.body.style.overflow = 'auto';
}

// Close modal when X is clicked
closeLogin.addEventListener('click', closeLoginModal);

// Close modal when overlay is clicked
modalOverlay.addEventListener('click', closeLoginModal);

// Prevent modal from closing when clicking inside it
loginModal.addEventListener('click', (e) => {
    e.stopPropagation();
});

/* ============================================
   FORM HANDLING
   ============================================ */
loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const remember = document.getElementById('remember').checked;
    
    // Here you would send the login data to your backend
    console.log('Login attempt:', { email, password, remember });
    
    // For now, show a success message
    alert('Login form submitted! (This is a frontend demo)\nEmail: ' + email);
    
    // Close modal
    closeLoginModal();
    
    // Reset form
    loginForm.reset();
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
    // This will navigate to the full-time questionnaire page
    alert('Navigating to Full-Time Questionnaire...\n\nThis would open the detailed questionnaire form.');
    // In production: window.location.href = '/analysis';
    console.log('Navigating to: /analysis (Full Time Learning Path)');
}

function navigateToQuickLearn() {
    // Navigate to the quick learning chatbot page
    window.location.href = 'quick-learner/index.html';
    console.log('Navigating to: Quick Learner Chatbot');
}

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
