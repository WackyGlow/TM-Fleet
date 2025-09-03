// Info Page JavaScript
// Handles statistics loading and dynamic content for the about page

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeInfoPage();
});

// Initialize the info page
function initializeInfoPage() {
    loadStatistics();
    startStatisticsRefresh();
    addInteractiveEffects();
}

// Load system statistics
async function loadStatistics() {
    try {
        // Load database statistics
        const response = await fetch('/db/stats');
        const stats = await response.json();

        updateStatistics(stats);

    } catch (error) {
        console.error('Error loading statistics:', error);
        showFallbackStats();
    }
}

// Update statistics in the UI
function updateStatistics(stats) {
    // Hero section stats
    updateElement('totalShips', formatNumber(stats.total_ships || 0));
    updateElement('activeShips', formatNumber(stats.active_ships_last_hour || 0));
    updateElement('managedShips', formatNumber(stats.tracked_ships || 0));

    // Technical section stats
    const totalRecords = (stats.total_ships || 0) + (stats.total_positions || 0);
    updateElement('dbRecords', formatNumber(totalRecords));

    // Cleanup section stats - show current record count
    updateElement('dbRecordsCleanup', formatNumber(totalRecords));

    // Add visual feedback for loaded stats
    animateStatCards();
}

// Update element content with null checking
function updateElement(id, content) {
    const element = document.getElementById(id);
    if (element) {
        // Add counting animation for numbers
        if (isNumeric(content)) {
            animateCount(element, parseInt(content.replace(/,/g, '')));
        } else {
            element.textContent = content;
        }
    }
}

// Check if content is numeric
function isNumeric(str) {
    return /^\d{1,3}(,\d{3})*$/.test(str) || /^\d+$/.test(str);
}

// Animate counting up to target number
function animateCount(element, target) {
    const duration = 1000; // 1 second
    const steps = 30;
    const stepValue = target / steps;
    const stepTime = duration / steps;

    let current = 0;

    const counter = setInterval(() => {
        current += stepValue;

        if (current >= target) {
            current = target;
            clearInterval(counter);
        }

        element.textContent = formatNumber(Math.floor(current));
    }, stepTime);
}

// Show fallback statistics when API fails
function showFallbackStats() {
    updateElement('totalShips', 'Loading...');
    updateElement('activeShips', 'Loading...');
    updateElement('managedShips', 'Loading...');
    updateElement('dbRecords', 'Loading...');
    updateElement('dbRecordsCleanup', 'Loading...');
}

// Format numbers with thousand separators
function formatNumber(num) {
    if (typeof num !== 'number') return num;
    return num.toLocaleString();
}

// Start periodic refresh of statistics
function startStatisticsRefresh() {
    // Refresh every 30 seconds
    setInterval(() => {
        loadStatistics();
    }, 30000);
}

// Add interactive effects
function addInteractiveEffects() {
    addHoverEffects();
    addScrollAnimations();
    addStatCardAnimations();
}

// Add hover effects to interactive elements
function addHoverEffects() {
    // Add hover effects to tech cards
    const techCards = document.querySelectorAll('.tech-card');
    techCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 12px 35px rgba(0,0,0,0.15)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 20px rgba(0,0,0,0.08)';
        });
    });

    // Add hover effects to mission points
    const missionPoints = document.querySelectorAll('.mission-point');
    missionPoints.forEach(point => {
        point.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
            this.style.boxShadow = '0 4px 15px rgba(0,0,0,0.1)';
        });

        point.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
            this.style.boxShadow = 'none';
        });
    });
}

// Add scroll-based animations
function addScrollAnimations() {
    // Create intersection observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');

                // Special handling for sections with staggered animations
                if (entry.target.classList.contains('tech-grid')) {
                    staggerTechCards(entry.target);
                }

                if (entry.target.classList.contains('mission-points')) {
                    staggerMissionPoints(entry.target);
                }
            }
        });
    }, observerOptions);

    // Observe sections for animation
    const sections = document.querySelectorAll('.section, .hero-section');
    sections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(section);
    });

    // Observe specific elements
    const techGrid = document.querySelector('.tech-grid');
    const missionPoints = document.querySelector('.mission-points');

    if (techGrid) observer.observe(techGrid);
    if (missionPoints) observer.observe(missionPoints);
}

// Stagger animation for tech cards
function staggerTechCards(container) {
    const cards = container.querySelectorAll('.tech-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';

        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Stagger animation for mission points
function staggerMissionPoints(container) {
    const points = container.querySelectorAll('.mission-point');
    points.forEach((point, index) => {
        point.style.opacity = '0';
        point.style.transform = 'translateX(-20px)';
        point.style.transition = 'opacity 0.4s ease, transform 0.4s ease';

        setTimeout(() => {
            point.style.opacity = '1';
            point.style.transform = 'translateX(0)';
        }, index * 150);
    });
}

// Animate stat cards
function animateStatCards() {
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.animation = `statCardPulse 0.6s ease ${index * 0.1}s`;
    });
}

// Add stat card animations
function addStatCardAnimations() {
    // Create keyframe animation for stat cards
    const style = document.createElement('style');
    style.textContent = `
        @keyframes statCardPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .fade-in {
            animation: fadeIn 0.6s ease forwards;
        }

        .section.fade-in,
        .hero-section.fade-in {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Page became visible, refresh stats
        loadStatistics();
    }
});

// Handle window focus
window.addEventListener('focus', function() {
    loadStatistics();
});

// Utility function for smooth scrolling (if needed)
function smoothScrollTo(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Handle potential errors gracefully
window.addEventListener('error', function(event) {
    console.error('JavaScript error on info page:', event.error);
});

// Performance monitoring
function logPerformanceMetrics() {
    if ('performance' in window) {
        const navigation = performance.getEntriesByType('navigation')[0];
        if (navigation) {
            console.log('Page load time:', navigation.loadEventEnd - navigation.loadEventStart, 'ms');
        }
    }
}

// Log performance metrics when page is fully loaded
window.addEventListener('load', function() {
    setTimeout(logPerformanceMetrics, 100);
});

// Export functions for potential external use
window.InfoPage = {
    loadStatistics,
    updateStatistics,
    smoothScrollTo
};