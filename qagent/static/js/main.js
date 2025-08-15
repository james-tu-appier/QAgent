// Main JavaScript for Test Planner Demo

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add fade-in animation to cards (without delay)
    const cards = document.querySelectorAll('.card');
    cards.forEach((card) => {
        card.classList.add('fade-in');
    });

    // File upload validation
    const fileInput = document.getElementById('prd_file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                // Check file size (10MB limit)
                const maxSize = 10 * 1024 * 1024;
                if (file.size > maxSize) {
                    showAlert('File size must be less than 10MB', 'danger');
                    this.value = '';
                    return;
                }

                // Check file type
                const allowedTypes = ['application/pdf', 'text/plain', 'text/markdown'];
                if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|txt|md)$/i)) {
                    showAlert('Please upload a PDF, TXT, or MD file', 'danger');
                    this.value = '';
                    return;
                }

                // Show success message
                showAlert(`File "${file.name}" selected successfully`, 'success');
            }
        });
    }

    // URL validation for Figma
    const figmaInput = document.getElementById('figma_url');
    if (figmaInput) {
        figmaInput.addEventListener('blur', function() {
            const url = this.value.trim();
            if (url && !isValidFigmaUrl(url)) {
                showAlert('Please enter a valid Figma URL', 'warning');
            }
        });
    }

    // Form submission handling
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const submitBtn = document.getElementById('submitBtn');
            const fileInput = document.getElementById('prd_file');
            const figmaInput = document.getElementById('figma_url');

            // Validate file
            if (!fileInput.files[0]) {
                e.preventDefault();
                showAlert('Please select a PRD file', 'danger');
                return;
            }

            // Validate Figma URL
            if (!figmaInput.value.trim()) {
                e.preventDefault();
                showAlert('Please enter a Figma URL', 'danger');
                return;
            }

            if (!isValidFigmaUrl(figmaInput.value.trim())) {
                e.preventDefault();
                showAlert('Please enter a valid Figma URL', 'danger');
                return;
            }

            // Show loading state
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            submitBtn.disabled = true;
            submitBtn.classList.add('btn-secondary');
            submitBtn.classList.remove('btn-primary');

            // Add loading overlay
            addLoadingOverlay();
        });
    }

    // Tab functionality enhancement
    const tabLinks = document.querySelectorAll('.nav-tabs .nav-link');
    tabLinks.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabLinks.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');
        });
    });

    // Copy to clipboard functionality
    window.copyToClipboard = function(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const text = element.textContent || element.innerText;
        
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(function() {
                showCopySuccess(event.target.closest('button'));
            }).catch(function(err) {
                console.error('Could not copy text: ', err);
                fallbackCopyTextToClipboard(text);
            });
        } else {
            fallbackCopyTextToClipboard(text);
        }
    };

    // No auto-refresh for results page
    // Removed automatic refresh to prevent unwanted page reloads
});

// Utility Functions

function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertContainer.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertContainer);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertContainer.parentNode) {
            alertContainer.remove();
        }
    }, 5000);
}

function isValidFigmaUrl(url) {
    const figmaPattern = /^https:\/\/www\.figma\.com\/(file|design)\/[a-zA-Z0-9]+/;
    return figmaPattern.test(url);
}

function addLoadingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    overlay.innerHTML = `
        <div class="text-center text-white">
            <div class="spinner-border mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <h5>Processing Your Test Plan</h5>
            <p>This may take a few minutes. Please don't close this page.</p>
            <div class="progress" style="width: 300px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 100%"></div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

function removeLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

function showCopySuccess(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-check"></i> Copied!';
    button.classList.remove('btn-outline-secondary');
    button.classList.add('btn-success');
    
    setTimeout(() => {
        button.innerHTML = originalText;
        button.classList.remove('btn-success');
        button.classList.add('btn-outline-secondary');
    }, 2000);
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.position = 'fixed';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showAlert('Text copied to clipboard!', 'success');
        } else {
            showAlert('Failed to copy text', 'danger');
        }
    } catch (err) {
        showAlert('Failed to copy text', 'danger');
    }
    
    document.body.removeChild(textArea);
}

// Export functions for global use
window.showAlert = showAlert;
window.isValidFigmaUrl = isValidFigmaUrl;
window.addLoadingOverlay = addLoadingOverlay;
window.removeLoadingOverlay = removeLoadingOverlay; 