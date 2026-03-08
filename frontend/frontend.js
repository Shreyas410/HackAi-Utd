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
const careerTrajectorySetupModal = document.getElementById('careerTrajectorySetupModal');
const closeCareerTrajectorySetup = document.getElementById('closeCareerTrajectorySetup');
const careerTrajectoryResultsModal = document.getElementById('careerTrajectoryResultsModal');
const closeCareerTrajectoryResults = document.getElementById('closeCareerTrajectoryResults');
const careerTrajectoryForm = document.getElementById('careerTrajectoryForm');
const ctLoadingIndicator = document.getElementById('ctLoadingIndicator');
const ctAnalyzeBtn = document.getElementById('ctAnalyzeBtn');
const scrollToCategories = document.getElementById('scrollToCategories');
const ctaButton = document.getElementById('ctaButton');
const themeToggleBtn = document.getElementById('themeToggleBtn');
const myProfileBtn = document.getElementById('myProfileBtn');
const userProfileModal = document.getElementById('userProfileModal');
const closeUserProfileModal = document.getElementById('closeUserProfileModal');
const upSaveBtn = document.getElementById('upSaveBtn');
const upReuploadBtn = document.getElementById('upReuploadBtn');
const upLoadingIndicator = document.getElementById('upLoadingIndicator');

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
   THEME FUNCTIONALITY (DARK MODE)
   ============================================ */
// Check for saved theme preference or system preference
const savedTheme = localStorage.getItem('theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
    document.body.classList.add('dark-mode');
    if (themeToggleBtn) {
        themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i>';
    }
}

if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');

        // Update icon
        themeToggleBtn.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';

        // Save preference
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
}

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
    modalTitle.textContent = 'Login to LearnPath';
    signupForm.style.display = 'none';
    loginForm.style.display = 'block';
});

// User Profile Modal events
myProfileBtn.addEventListener('click', openUserProfileModal);
closeUserProfileModal.addEventListener('click', closeUserProfileModalFunc);

// Close modal when X is clicked
closeLogin.addEventListener('click', closeLoginModal);
closeQuickLearn.addEventListener('click', closeQuickLearnModal);
closeCareerTrajectorySetup.addEventListener('click', closeCareerTrajectorySetupModal);
closeCareerTrajectoryResults.addEventListener('click', closeCareerTrajectoryResultsModal);

// Close modal when overlay is clicked or by clicking outside specific modals
window.addEventListener('click', (e) => {
    if (e.target === loginModal) {
        closeLoginModal();
    }
    if (e.target === quickLearnModal) {
        closeQuickLearnModal();
    }
    if (e.target === careerTrajectorySetupModal) {
        closeCareerTrajectorySetupModal();
    }
    if (e.target === careerTrajectoryResultsModal) {
        closeCareerTrajectoryResultsModal();
    }
    if (e.target === userProfileModal) {
        closeUserProfileModalFunc();
    }
});
modalOverlay.addEventListener('click', () => {
    closeLoginModal();
    closeQuickLearnModal();
    closeCareerTrajectorySetupModal();
    closeCareerTrajectoryResultsModal();
    closeUserProfileModalFunc(); // Also close user profile if open
});

// Prevent modal from closing when clicking inside it
loginModal.addEventListener('click', (e) => {
    e.stopPropagation();
});
quickLearnModal.addEventListener('click', (e) => {
    e.stopPropagation();
});
careerTrajectorySetupModal.addEventListener('click', (e) => {
    e.stopPropagation();
});
careerTrajectoryResultsModal.addEventListener('click', (e) => {
    e.stopPropagation();
});
userProfileModal.addEventListener('click', (e) => {
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
    if (!loginModal.classList.contains('show') && !careerTrajectorySetupModal.classList.contains('show') && !careerTrajectoryResultsModal.classList.contains('show') && !userProfileModal.classList.contains('show')) {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

function openCareerTrajectoryModal() {
    careerTrajectorySetupModal.classList.add('show');
    modalOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeCareerTrajectorySetupModal() {
    careerTrajectorySetupModal.classList.remove('show');
    if (!loginModal.classList.contains('show') && !quickLearnModal.classList.contains('show') && !careerTrajectoryResultsModal.classList.contains('show') && !userProfileModal.classList.contains('show')) {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

function openCareerTrajectoryResultsModal() {
    careerTrajectoryResultsModal.classList.add('show');
    modalOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeCareerTrajectoryResultsModal() {
    careerTrajectoryResultsModal.classList.remove('show');
    if (!loginModal.classList.contains('show') && !quickLearnModal.classList.contains('show') && !careerTrajectorySetupModal.classList.contains('show') && !userProfileModal.classList.contains('show')) {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

function openUserProfileModal() {
    userProfileModal.classList.add('show');
    modalOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
    fetchUserProfile();
}

function closeUserProfileModalFunc() {
    userProfileModal.classList.remove('show');
    if (!loginModal.classList.contains('show') && !quickLearnModal.classList.contains('show') && !careerTrajectorySetupModal.classList.contains('show') && !careerTrajectoryResultsModal.classList.contains('show')) {
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
            myProfileBtn.style.display = 'block'; // Show profile button on login
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

function navigateToCareerTrajectory() {
    if (!isUserLoggedIn()) {
        alert("Please log in first to access Career Trajectory analysis.");
        openLoginModal();
        return;
    }
    openCareerTrajectoryModal();
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
    // Check login status on load
    if (isUserLoggedIn()) {
        myProfileBtn.style.display = 'block';
    } else {
        myProfileBtn.style.display = 'none';
    }
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
    closeUserProfileModalFunc(); // Close profile modal if open
    myProfileBtn.style.display = 'none';
    console.log('User logged out');
}

/* ============================================
   USER PROFILE LOGIC
   ============================================ */
async function fetchUserProfile() {
    const userId = localStorage.getItem('authToken');
    if (!userId) {
        alert("Please login first to view your profile.");
        closeUserProfileModalFunc();
        return;
    }

    try {
        const response = await fetch(`/api/profile/${userId}`);
        const data = await response.json();

        if (response.ok) {
            document.getElementById('upName').value = data.name || '';
            document.getElementById('upEducation').value = (data.education || []).join('\n');
            document.getElementById('upExperience').value = (data.work_experience || []).join('\n');
            document.getElementById('upSkills').value = (data.skills || []).join(', ');
            document.getElementById('upCertifications').value = (data.certifications || []).join(', ');
        } else {
            console.warn("Could not fetch profile", data.detail);
        }
    } catch (e) {
        console.error("Error fetching profile", e);
    }
}

upSaveBtn.addEventListener('click', async () => {
    const userId = localStorage.getItem('authToken');
    if (!userId) return;

    upSaveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    upSaveBtn.disabled = true;

    const profileData = {
        user_id: userId,
        name: document.getElementById('upName').value,
        education: document.getElementById('upEducation').value.split('\n').filter(s => s.trim() !== ''),
        work_experience: document.getElementById('upExperience').value.split('\n').filter(s => s.trim() !== ''),
        skills: document.getElementById('upSkills').value.split(',').map(s => s.trim()).filter(s => s !== ''),
        certifications: document.getElementById('upCertifications').value.split(',').map(s => s.trim()).filter(s => s !== ''),
        publications: [], // Not exposed in basic UI yet
        resume_text: ""   // Usually backend overrides or keeps existing if empty
    };

    try {
        const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData)
        });

        if (response.ok) {
            alert("Profile saved successfully!");
            closeUserProfileModalFunc();
        } else {
            alert("Failed to save profile.");
        }
    } catch (e) {
        console.error(e);
        alert("Error making network request.");
    } finally {
        upSaveBtn.innerHTML = '<i class="fas fa-save"></i> Save Profile';
        upSaveBtn.disabled = false;
    }
});

upReuploadBtn.addEventListener('click', async () => {
    const userId = localStorage.getItem('authToken');
    if (!userId) return;

    const resumeInput = document.getElementById('upResumeReupload');
    if (!resumeInput.files[0]) {
        alert("Please select a new resume to re-scan.");
        return;
    }

    const formData = new FormData();
    formData.append('resume', resumeInput.files[0]);
    formData.append('user_id', userId);

    upReuploadBtn.style.display = 'none';
    upLoadingIndicator.style.display = 'block';

    try {
        const response = await fetch('/api/career-trajectory/analyze-resume', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            // Fetch immediately again to populate fields
            await fetchUserProfile();
            alert("Profile updated with details from fresh scan.");
        } else {
            const data = await response.json();
            alert("Failed to analyze resume: " + (data.detail || 'Unknown error.'));
        }
    } catch (e) {
        console.error(e);
        alert("An error occurred during re-upload.");
    } finally {
        upReuploadBtn.style.display = 'block';
        upLoadingIndicator.style.display = 'none';
        resumeInput.value = '';
    }
});

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
    navigateToCareerTrajectory,
    submitFullTimeQuestionnaire,
    submitQuickLearnRequest,
    isUserLoggedIn,
    storeAuthToken,
    logoutUser
};

/* ============================================
   CAREER TRAJECTORY LOGIC
   ============================================ */
const ctStep1 = document.getElementById('ctStep1');
const ctStep2 = document.getElementById('ctStep2');
const ctGenerateRoadmapBtn = document.getElementById('ctGenerateRoadmapBtn');
const ctSuggestedRolesList = document.getElementById('ctSuggestedRolesList');
const ctExtractedText = document.getElementById('ctExtractedText');
const ctTargetRoleInput = document.getElementById('ctTargetRole');
const ctLoadingMessage = document.getElementById('ctLoadingMessage');

ctAnalyzeBtn.addEventListener('click', async () => {
    const resumeInput = document.getElementById('ctResume');

    if (!resumeInput.files[0]) {
        alert("Please upload a resume.");
        return;
    }

    const formData = new FormData();
    formData.append('resume', resumeInput.files[0]);
    if (isUserLoggedIn()) {
        formData.append('user_id', localStorage.getItem('authToken'));
    }

    ctStep1.style.display = 'none';
    ctLoadingMessage.textContent = 'Analyzing resume...';
    ctLoadingIndicator.style.display = 'block';

    try {
        const response = await fetch('/api/career-trajectory/analyze-resume', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.analysis && data.analysis.suggested_roles) {
            ctExtractedText.value = data.extracted_text;

            // Render suggested roles as clickable badges
            ctSuggestedRolesList.innerHTML = '';
            data.analysis.suggested_roles.forEach(role => {
                const badge = document.createElement('span');
                badge.className = 'role-badge';
                badge.style.cssText = 'background: rgba(99, 102, 241, 0.1); color: var(--primary-color); border: 1px solid var(--primary-color); padding: 6px 12px; border-radius: 20px; font-size: 0.85em; cursor: pointer; transition: all 0.2s;';
                badge.textContent = role;
                badge.onmouseover = () => { badge.style.background = 'var(--primary-color)'; badge.style.color = 'white'; };
                badge.onmouseout = () => { badge.style.background = 'rgba(99, 102, 241, 0.1)'; badge.style.color = 'var(--primary-color)'; };
                badge.onclick = () => { ctTargetRoleInput.value = role; };
                ctSuggestedRolesList.appendChild(badge);
            });

            ctStep2.style.display = 'block';
        } else {
            alert('Failed to analyze resume: ' + (data.detail || data.analysis?.error || 'Unknown error.'));
            ctStep1.style.display = 'block';
        }
    } catch (error) {
        console.error('Error analyzing resume:', error);
        alert('An error occurred during analysis.');
        ctStep1.style.display = 'block';
    } finally {
        ctLoadingIndicator.style.display = 'none';
    }
});

ctGenerateRoadmapBtn.addEventListener('click', async () => {
    const targetRole = ctTargetRoleInput.value.trim();
    if (!targetRole) {
        alert("Please select or enter a target role.");
        return;
    }

    ctStep2.style.display = 'none';
    ctLoadingMessage.textContent = 'Generating interactive career roadmap...';
    ctLoadingIndicator.style.display = 'block';

    try {
        const response = await fetch('/api/career-trajectory/roadmap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: ctExtractedText.value,
                target_role: targetRole
            })
        });

        const data = await response.json();

        if (response.ok && !data.error) {
            closeCareerTrajectorySetupModal();
            renderCareerTrajectoryResults(data);
            openCareerTrajectoryResultsModal();
        } else {
            alert('Failed to generate roadmap: ' + (data.detail || data.error || 'Unknown error.'));
            ctStep2.style.display = 'block';
        }
    } catch (error) {
        console.error('Error generating roadmap:', error);
        alert('An error occurred during roadmap generation.');
        ctStep2.style.display = 'block';
    } finally {
        ctLoadingIndicator.style.display = 'none';
        // Give time for modal closing transitions, then reset setup modal
        setTimeout(() => {
            ctStep1.style.display = 'block';
            ctStep2.style.display = 'none';
            document.getElementById('ctResume').value = '';
            ctTargetRoleInput.value = '';
        }, 500);
    }
});

function renderCareerTrajectoryResults(data) {
    const container = document.getElementById('ctResultsContent');
    container.innerHTML = '';

    if (data.error) {
        container.innerHTML = `<div style="color:red;">Error: ${data.error}</div>`;
        return;
    }

    // Required Skills
    let skillsHtml = '<h3><i class="fas fa-laptop-code"></i> Skills Gap (To Acquire)</h3><div class="skills-gap-container" style="margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px;">';
    if (data.skills_to_acquire) {
        data.skills_to_acquire.forEach(skill => {
            skillsHtml += `<span class="skill-tag" style="background: var(--primary-color); color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9em;">${skill}</span>`;
        });
    }
    skillsHtml += '</div>';

    // Certifications
    let certsHtml = '<h3><i class="fas fa-certificate"></i> Suggested Certifications</h3><ul class="certs-list" style="margin-bottom: 20px;">';
    if (data.certifications) {
        data.certifications.forEach(cert => {
            certsHtml += `<li style="margin-bottom: 5px;"><strong>${cert.name}</strong>: ${cert.reason}</li>`;
        });
    }
    certsHtml += '</ul>';

    // Mind Tree
    let treeHtml = '<h3><i class="fas fa-network-wired"></i> Career Mind Tree</h3><div class="mind-tree-container" style="margin-bottom: 20px; border-left: 2px solid var(--primary-color); padding-left: 20px;">';
    if (data.mind_tree) {
        data.mind_tree.forEach((node, index) => {
            treeHtml += `
                <div class="tree-node" style="margin-bottom: 15px; position: relative;">
                    <div class="node-icon" style="position: absolute; left: -32px; top: 0; background: var(--bg-color); color: var(--primary-color); width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid var(--primary-color);">${index + 1}</div>
                    <div class="node-content">
                        <h4 style="margin-bottom: 5px; color: var(--text-color);">${node.step}</h4>
                        <p style="color: var(--text-light); font-size: 0.95em; line-height: 1.5;">${node.description}</p>
                    </div>
                </div>`;
        });
    }
    treeHtml += '</div>';

    container.innerHTML = skillsHtml + certsHtml + treeHtml;
}

function navigateToQuickLearnFromCT() {
    closeCareerTrajectoryResultsModal();
    navigateToQuickLearn();
}
