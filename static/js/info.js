// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeInfoPage();
});


// Initialize the info page
function initializeInfoPage() {
    loadStatistics();
    loadPositionStatistics();
    loadAISServiceStatus();
    loadDatabaseStats();
    setupEventListeners();
    startStatisticsRefresh();
    addInteractiveEffects();
}

// Setup event listeners for buttons
function setupEventListeners() {
    // Position Stats button
    const refreshPositionBtn = document.getElementById('refreshPositionStatsBtn');
    if (refreshPositionBtn) {
        refreshPositionBtn.addEventListener('click', loadPositionStatistics);
    }

    // Status cleanup button
    const statusCleanupBtn = document.getElementById('statusCleanupBtn');
    if (statusCleanupBtn) {
        statusCleanupBtn.addEventListener('click', performStatusCleanup);
    }

    // Database refresh button
    const refreshStatsBtn = document.getElementById('refreshStatsBtn');
    if (refreshStatsBtn) {
        refreshStatsBtn.addEventListener('click', loadDatabaseStats);
    }

    // Database cleanup button
    const cleanupBtn = document.getElementById('cleanupBtn');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', performDatabaseCleanup);
    }
}

// Load basic system statistics
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

// Load position statistics for cleanup analysis
async function loadPositionStatistics() {
    try {
        const response = await fetch('/api/cleanup/age-stats');
        const data = await response.json();

        updatePositionStatistics(data);
        enableCleanupButton();

    } catch (error) {
        console.error('Error loading position statistics:', error);
        showMessage('positionStatsMessage', 'Error loading position statistics: ' + error.message, 'error');
    }
}

// Load AIS service status
async function loadAISServiceStatus() {
    try {
        const response = await fetch('/api/cleanup/status');
        const data = await response.json();

        updateAISServiceStatus(data);

    } catch (error) {
        console.error('Error loading AIS service status:', error);
        // Try fallback config endpoint
        try {
            const configResponse = await fetch('/api/cleanup/config');
            const configData = await configResponse.json();
            updateAISServiceConfig(configData);
        } catch (configError) {
            console.error('Error loading AIS config:', configError);
        }
    }
}

// Load database maintenance statistics
async function loadDatabaseStats() {
    try {
        const response = await fetch('/admin/cleanup-stats');
        const data = await response.json();

        updateDatabaseStats(data);
        enableDatabaseCleanupButton();

    } catch (error) {
        console.error('Error loading database stats:', error);
        showMessage('cleanupMessage', 'Error loading database statistics: ' + error.message, 'error');
    }
}

// Update basic statistics in the UI
function updateStatistics(stats) {
    // Hero section stats
    updateElement('totalShips', formatNumber(stats.total_ships || 0));
    updateElement('activeShips', formatNumber(stats.active_ships_last_hour || 0));
    updateElement('managedShips', formatNumber(stats.tracked_ships || 0));

    // Technical section stats
    const totalRecords = (stats.total_ships || 0) + (stats.total_positions || 0);
    updateElement('dbRecords', formatNumber(totalRecords));
    updateElement('aisMessageCount', formatNumber(stats.total_positions || 0));

    // Add visual feedback for loaded stats
    animateStatCards();
}

// Update position statistics
function updatePositionStatistics(data) {
    if (data.error) {
        showMessage('positionStatsMessage', 'Error: ' + data.error, 'error');
        return;
    }

    // Sailing ships data
    updateElement('sailingShips', formatNumber(data.underway_ships || 0));
    updateElement('sailingPositions', formatNumber(data.underway_total_positions || 0));
    updateElement('sailingOldPositions', formatNumber(data.old_underway_positions || 0));

    // Moored ships data
    updateElement('mooredShips', formatNumber(data.moored_ships || 0));
    updateElement('mooredPositions', formatNumber(data.moored_total_positions || 0));
    updateElement('mooredOldPositions', formatNumber(data.old_moored_positions || 0));

    // Unknown status data
    updateElement('unknownPositions', formatNumber(data.unknown_total_positions || 0));
    updateElement('unknownOldPositions', formatNumber(data.unknown_old_positions || 0));

    // Total cleanup candidates
    const totalCleanup = (data.underway_old_positions || 0) + (data.moored_old_positions || 0) + (data.unknown_old_positions || 0);
    updateElement('cleanupCandidates', formatNumber(totalCleanup));

    // Show success message
    hideMessage('positionStatsMessage');
}

let cleanupCountdownTimer = null;
let cleanupState = { target: null, token: null };

// Update AIS service status
function updateAISServiceStatus(data = {}) {
    // single global state (no top-level lets)
    if (!window.cleanupState) window.cleanupState = { timer: null, target: null, token: null };
    const S = window.cleanupState;

    // basic stats
    updateElement('messageCount', formatNumber(num(data.messages_processed, 0)));

    // config (supports old/new keys)
    const enabled = bool(data.status_cleanup_enabled, data.age_cleanup_enabled, false);
    const active  = !!data.cleanup_timer_active;
    const intervalMin = num(data.status_cleanup_interval_minutes, 0);

    updateElement('sailingTimeoutConfig', pluralize(num(data.underway_timeout_minutes, 2), 'minute'));
    updateElement('mooredTimeoutConfig',  pluralize(num(data.moored_timeout_hours, 2), 'hour'));
    updateElement('cleanupIntervalConfig',
        intervalMin > 0 ? pluralize(intervalMin, 'minute') : formatNumber(num(data.age_cleanup_interval, 0))
    );
    updateElement('statusCleanupEnabled', enabled ? 'Enabled' : 'Disabled');

    // last cleanup text (priority: time → msg → scheduled → never)
    const lastISO = data.last_status_cleanup_time;
    const lastMsg = num(data.last_age_cleanup_at_message, 0);
    if (lastISO) {
        const t = new Date(lastISO).toLocaleTimeString();
        updateElement('lastStatusCleanup', `${t} | ${data.last_status_cleanup_success ? '✅ Success' : '❌ Failed'}`);
    } else if (lastMsg > 0) {
        updateElement('lastStatusCleanup', `at message ${formatNumber(lastMsg)}`);
    } else {
        updateElement('lastStatusCleanup', enabled && active ? 'Scheduled (no runs yet)' : 'Never');
    }

    // next cleanup (countdown)
    if (!(enabled && active && intervalMin > 0)) {
        stopCountdown(S);
        updateElement('nextStatusCleanup', 'Not scheduled');
        S.target = null; S.token = null;
        return;
    }

    // prefer backend next time; else last+interval; else keep previous; else now+interval
    let target =
        data.next_status_cleanup_time ? new Date(data.next_status_cleanup_time) :
        lastISO ? new Date(new Date(lastISO).getTime() + intervalMin * 60000) :
        (S.target || new Date(Date.now() + intervalMin * 60000));

    // clamp past/near-past to avoid “Due now” flicker
    if (target.getTime() - Date.now() <= 1500) {
        target = new Date(Date.now() + intervalMin * 60000);
    }

    // restart countdown only if meaningful change (new token or >1s drift)
    const token = (lastISO || '') + '|' + intervalMin;
    const changed = !S.target || Math.abs(target - S.target) > 1000 || token !== S.token;
    if (changed) {
        S.target = target; S.token = token;
        startCountdown(S, target);
    }
}

/* ── tiny helpers (no globals) ───────────────────────── */

function num(v, fallback) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
}

function bool(a, b, fallback) {
    if (typeof a === 'boolean') return a;
    if (typeof b === 'boolean') return b;
    return !!fallback;
}

function pluralize(value, unit) {
    const n = num(value, 0);
    return `${n} ${unit}${n === 1 ? '' : 's'}`;
}

function startCountdown(S, targetDate) {
    stopCountdown(S);
    function tick() {
        const diff = targetDate.getTime() - Date.now();
        if (diff <= 1500) { updateElement('nextStatusCleanup', 'Due now'); return; }
        const m = Math.floor(diff / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        updateElement('nextStatusCleanup', `in ${m}m ${s}s`);
    }
    tick();
    S.timer = setInterval(tick, 1000);
}

function stopCountdown(S) {
    if (S.timer) { clearInterval(S.timer); S.timer = null; }
}


// Update AIS service config (fallback)
function updateAISServiceConfig(data) {
    updateElement('sailingTimeoutConfig', (data.position_max_age_hours * 60 || 120) + ' minutes');
    updateElement('mooredTimeoutConfig', (data.ship_max_age_hours || 24) + ' hours');
    updateElement('cleanupIntervalConfig', formatNumber(data.age_cleanup_interval || 1000));
    updateElement('statusCleanupEnabled', data.auto_cleanup_enabled ? 'Enabled' : 'Disabled');
}

// Update database maintenance statistics
function updateDatabaseStats(data) {
    updateElement('totalPositions', formatNumber(data.total_positions || 0));
    updateElement('uniqueShips', formatNumber(data.unique_ships || 0));
    updateElement('duplicatePositions', formatNumber(data.duplicate_positions || 0));

    hideMessage('cleanupMessage');
}

// Perform status-based cleanup
async function performStatusCleanup() {
    const button = document.getElementById('statusCleanupBtn');
    if (!button) return;

    button.disabled = true;
    button.textContent = '🧹 Cleaning...';

    try {
        const response = await fetch('/api/cleanup/age-cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                underway_minutes: 2,
                moored_hours: 2
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage('positionStatsMessage', result.message, 'success');
            loadPositionStatistics(); // Refresh stats
        } else {
            showMessage('positionStatsMessage', result.message, 'error');
        }

    } catch (error) {
        showMessage('positionStatsMessage', 'Cleanup failed: ' + error.message, 'error');
    } finally {
        button.disabled = false;
        button.textContent = '🧹 Status-Based Cleanup';
    }
}

// Perform database cleanup
async function performDatabaseCleanup() {
    const button = document.getElementById('cleanupBtn');
    if (!button) return;

    if (!confirm('This will remove old position records to optimize database performance. Continue?')) {
        return;
    }

    button.disabled = true;
    button.textContent = '🧹 Cleaning...';

    try {
        const response = await fetch('/admin/cleanup-positions', {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showMessage('cleanupMessage', result.message, 'success');
            loadDatabaseStats(); // Refresh stats
        } else {
            showMessage('cleanupMessage', result.message, 'error');
        }

    } catch (error) {
        showMessage('cleanupMessage', 'Cleanup failed: ' + error.message, 'error');
    } finally {
        button.disabled = false;
        button.textContent = '🧹 Clean Up Old Records';
    }
}

// Enable cleanup buttons when data is loaded
function enableCleanupButton() {
    const button = document.getElementById('statusCleanupBtn');
    if (button) {
        button.disabled = false;
    }
}

function enableDatabaseCleanupButton() {
    const button = document.getElementById('cleanupBtn');
    if (button) {
        button.disabled = false;
    }
}

// Show/hide messages
function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = message;
    element.className = `cleanup-message ${type}`;
    element.style.display = 'block';

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

function hideMessage(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'none';
    }
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
    updateElement('aisMessageCount', 'Loading...');
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
        loadPositionStatistics();
        loadAISServiceStatus();
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

        .cleanup-message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            font-weight: bold;
        }

        .cleanup-message.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .cleanup-message.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .cleanup-btn {
            padding: 8px 16px;
            margin: 5px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }

        .cleanup-btn.primary {
            background-color: #007bff;
            color: white;
        }

        .cleanup-btn.secondary {
            background-color: #6c757d;
            color: white;
        }

        .cleanup-btn:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
            opacity: 0.6;
        }
    `;
    document.head.appendChild(style);
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Page became visible, refresh stats
        loadStatistics();
        loadPositionStatistics();
        loadAISServiceStatus();
    }
});

// Handle window focus
window.addEventListener('focus', function() {
    loadStatistics();
    loadPositionStatistics();
    loadAISServiceStatus();
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

function startCleanupCountdown(nextTime) {
    function updateCountdown() {
        const now = new Date();
        const diffMs = nextTime - now;

        if (diffMs <= 0) {
            updateElement('nextStatusCleanup', 'Due now');
            return;
        }

        const minutes = Math.floor(diffMs / 60000);
        const seconds = Math.floor((diffMs % 60000) / 1000);
        updateElement('nextStatusCleanup', `in ${minutes}m ${seconds}s`);
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
}


// Log performance metrics when page is fully loaded
window.addEventListener('load', function() {
    setTimeout(logPerformanceMetrics, 100);
});

// Export functions for potential external use
window.InfoPage = {
    loadStatistics,
    loadPositionStatistics,
    loadAISServiceStatus,
    loadDatabaseStats,
    updateStatistics,
    smoothScrollTo
};