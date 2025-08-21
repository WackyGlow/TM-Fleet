// Authentication JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeAuthPage();
});

function initializeAuthPage() {
    setupFormHandlers();
    setupKeyboardNavigation();
    autoFocusUsername();
}

function setupFormHandlers() {
    const form = document.getElementById('loginForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmission);
    }
}

function handleFormSubmission() {
    const button = document.getElementById('loginButton');
    const buttonText = document.getElementById('buttonText');

    if (button) {
        button.disabled = true;
        button.classList.add('loading');

        if (buttonText) {
            buttonText.textContent = 'Signing In...';
        } else {
            button.textContent = 'Signing In...';
        }
    }
}

function setupKeyboardNavigation() {
    // Handle Enter key navigation between fields
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');

    if (usernameField && passwordField) {
        usernameField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                passwordField.focus();
            }
        });
    }
}

function autoFocusUsername() {
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.focus();
    }
}

function validateForm() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showAlert('Please enter both username and password.', 'error');
        resetButtonState();
        return false;
    }

    return true;
}

function showAlert(message, type) {
    // Create alert element if it doesn't exist
    let alertContainer = document.querySelector('.alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.className = 'alert-container';

        const form = document.getElementById('loginForm');
        if (form) {
            form.insertBefore(alertContainer, form.firstChild);
        }
    }

    alertContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertContainer.innerHTML = '';
    }, 5000);
}

function resetButtonState() {
    const button = document.getElementById('loginButton');
    const buttonText = document.getElementById('buttonText');

    if (button) {
        button.disabled = false;
        button.classList.remove('loading');

        if (buttonText) {
            buttonText.textContent = 'Sign In';
        } else {
            button.textContent = 'Sign In';
        }
    }
}

// Enhanced form validation
function enhanceFormValidation() {
    const form = document.getElementById('loginForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
        });
    }
}

// Initialize enhanced validation
document.addEventListener('DOMContentLoaded', function() {
    enhanceFormValidation();
});