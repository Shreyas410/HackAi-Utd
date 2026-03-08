# LearnPath Frontend

A modern, responsive frontend for the personalized learning platform that helps users discover the best courses tailored to their needs.

## 📁 Project Structure

```
frontend/
├── index.html          # Main HTML file
├── styles.css          # Complete styling and animations
├── frontend.js         # Interactive JavaScript functionality
└── README.md          # This file
```

## ✨ Features

### 📱 Responsive Design
- Fully responsive for desktop, tablet, and mobile devices
- Mobile-first approach with smooth breakpoints
- Hamburger menu for mobile navigation

### 🎯 Two Learning Paths

#### 1. **Full Time Learner Path**
- Detailed questionnaire to assess learning goals and background
- Automatic categorization (Beginner, Intermediate, Advanced)
- Personalized course recommendations from:
  - YouTube
  - Coursera
  - Udemy
- Comprehensive learning experience

#### 2. **Quick Learner Path**
- Time selection (10, 15, or 20 minutes)
- AI-powered summaries via Gemini API
- Quick course recommendations
- Perfect for busy professionals

### 🎨 Design Features
- Modern gradient color scheme
- Smooth animations and transitions
- Floating card animations in hero section
- Timeline visualization for workflows
- Interactive modal for login
- Hover effects on all interactive elements

### 🔐 Authentication
- Login modal with email/password fields
- Social login placeholder (Google)
- Remember me functionality
- Form validation ready

### 📊 Information Sections
- Hero section with engaging copy
- "How it Works" section with detailed workflows
- Features section highlighting key benefits
- Footer with social links and sitemap

## 🚀 Quick Start

1. Open the `index.html` file in a modern web browser
2. Click on "Get Started" to navigate to categories
3. Choose between "Full Time Learner" or "Quick Learner"
4. Use the "Login" button to test the authentication modal

## 🎮 Interactive Elements

### Navigation
- Sticky navbar that updates on scroll
- Smooth scroll to sections
- Active link highlighting

### Buttons
- Primary CTA buttons with gradient and shadow effects
- Secondary outline buttons
- Block buttons for full width
- Keyboard shortcuts:
  - **Alt+Q**: Navigate to Quick Learn
  - **Alt+F**: Navigate to Full Time
  - **Esc**: Close login modal

### Forms
- Login form with validation ready
- Smooth input focus states
- Form divider with styled text

### Cards & Animations
- Floating card animations in hero
- Bounce scroll indicator
- Staggered animation on feature cards
- Slide animations on section entry

## 🔗 Integration Points

### Backend Routes
The frontend expects the following backend routes:

```
POST /analysis           # Full time questionnaire submission
POST /multipleAnalysis   # Quick learning request submission
```

### API Endpoints to Implement
```javascript
// In frontend.js - Update these functions with your backend API:

// 1. Submit questionnaire answers
submitFullTimeQuestionnaire(formData)

// 2. Submit quick learning request
submitQuickLearnRequest(topic, timeMinutes)

// 3. Authentication
storeAuthToken(token)        // Store JWT after login
isUserLoggedIn()             // Check authentication state
logoutUser()                 // Clear authentication
```

## 🎨 Customization

### Colors
Edit the CSS variables in `styles.css`:
```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #ec4899;
    --accent-color: #f59e0b;
    /* ... more variables */
}
```

### Typography
- Heading fonts: Segoe UI, Tahoma, Geneva, Verdana
- Easily changeable in `styles.css`

### Animations
- Duration: 0.3s - 0.8s
- Easing: cubic-bezier(0.4, 0, 0.2, 1)
- Predefined keyframes: slideInLeft, slideInRight, slideUp, float, bounce

## 🔧 JavaScript API

### Public Methods (Available via window.LearnPath)

```javascript
// Modal control
LearnPath.openLoginModal()
LearnPath.closeLoginModal()

// Navigation
LearnPath.navigateToFullTime()
LearnPath.navigateToQuickLearn()

// Form submission
LearnPath.submitFullTimeQuestionnaire(formData)
LearnPath.submitQuickLearnRequest(topic, timeMinutes)

// Authentication
LearnPath.isUserLoggedIn()
LearnPath.storeAuthToken(token)
LearnPath.logoutUser()
```

## 📝 Form Fields (Login)

```html
- Email Address (required)
- Password (required)
- Remember me (checkbox)
- Google OAuth option (placeholder)
```

## 🌐 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 📱 Responsive Breakpoints

```css
Desktop:    > 1024px
Tablet:     768px - 1024px
Mobile:     < 768px
Small Mobile: < 480px
```

## 🎯 Next Steps for Integration

1. **Create Questionnaire Form** (`/pages/questionnaire.html`)
   - Integrate with `navigateToFullTime()`
   - POST to `/analysis` endpoint

2. **Create Time Selection Form** (`/pages/quick-learn.html`)
   - Integrate with `navigateToQuickLearn()`
   - POST to `/multipleAnalysis` endpoint

3. **Create Results/Recommendations Page**
   - Display course recommendations
   - Integrate with backend course fetching

4. **Create User Dashboard** (`/pages/dashboard.html`)
   - Track enrolled courses
   - View progress
   - Saved preferences

5. **Implement Backend Authentication**
   - Login endpoint
   - JWT token generation
   - User session management

6. **Add API Integration**
   - Replace alert() calls with actual API requests
   - Add loading indicators
   - Implement error handling

## 📄 File Descriptions

### index.html
- Complete semantic HTML structure
- Meta tags for responsiveness
- Font Awesome icons integration
- All necessary sections and modals

### styles.css
- Complete styling (5000+ lines)
- CSS Grid and Flexbox layouts
- Animations and transitions
- Dark/light color themes
- Mobile-first responsive design

### frontend.js
- Event listeners setup
- Modal management
- Form handling
- Navigation functionality
- Intersection Observer for animations
- Helper functions for backend integration

## 🤝 Contributing

To modify or extend the frontend:

1. Maintain the existing HTML structure
2. Follow the CSS variable naming conventions
3. Use the established animation library
4. Keep JavaScript functions organized by category

## 📞 Support

For implementation questions or integration help, refer to the commented sections in each file.

## 📄 License

This frontend is part of the "Suggesting Best Courses using Sentiment Analysis" project.

---

**Ready to integrate?** Start with updating the `submitFullTimeQuestionnaire()` and `submitQuickLearnRequest()` functions to connect with your backend!
