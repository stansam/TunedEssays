
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

/**
 * Initialize dashboard functionality
 */
function initializeDashboard() {
    // Initialize components
    initializeAnimations();
    initializeTooltips();
    initializeCounters();
    initializeRefreshFunctionality();
    initializeNotifications();
    initializeResponsiveHandlers();
    
    console.log('Dashboard initialized successfully');
}

/**
 * Initialize smooth animations for dashboard elements
 */
function initializeAnimations() {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.metric-card, .status-card, .dashboard-card');
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.classList.add('fade-in');
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    cards.forEach(card => {
        observer.observe(card);
    });
}

/**
 * Initialize Bootstrap tooltips for interactive elements
 */
function initializeTooltips() {
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

/**
 * Initialize animated counters for metric numbers
 */
function initializeCounters() {
    const counters = document.querySelectorAll('.metric-number');
    
    const animateCounter = (element) => {
        const target = parseInt(element.textContent.replace('$', ''));
        const duration = 1000; // 2 seconds
        const increment = target / (duration / 16); // 60 FPS
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                element.textContent = formatNumber(Math.floor(current));
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = formatNumber(target);
            }
        };
        
        updateCounter();
    };
    
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                counterObserver.unobserve(entry.target);
            }
        });
    });
    
    counters.forEach(counter => {
        counterObserver.observe(counter);
    });
}

/**
 * Format numbers for display
 */
function formatNumber(num) {
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Initialize refresh functionality
 */
function initializeRefreshFunctionality() {
    // Add refresh functionality to the sync button
    const refreshBtn = document.querySelector('.btn-outline-primary[onclick="refreshDashboard()"]');
    if (refreshBtn) {
        refreshBtn.removeAttribute('onclick');
        refreshBtn.addEventListener('click', handleRefreshDashboard);
    }
}

/**
 * Handle dashboard refresh
 */
function handleRefreshDashboard(event) {
    event.preventDefault();
    
    const btn = event.target.closest('button');
    const icon = btn.querySelector('i');
    
    // Add loading state
    btn.disabled = true;
    icon.classList.add('fa-spin');
    
    // Simulate refresh (in real app, this would make an AJAX call)
    setTimeout(() => {
        // Remove loading state
        btn.disabled = false;
        icon.classList.remove('fa-spin');
        
        // Show success message
        showNotification('Dashboard refreshed successfully!', 'success');
        
        // Optionally reload the page for real refresh
        // window.location.reload();
    }, 1500);
}

/**
 * Initialize notification system
 */
function initializeNotifications() {
    // Add click handlers for notification items
    const notificationItems = document.querySelectorAll('.notification-item');
    
    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            // Mark as read visually
            this.style.opacity = '0.6';
            
            // In a real app, you would make an AJAX call to mark as read
            console.log('Notification clicked:', this);
        });
    });
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 350px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        border: none;
        border-radius: 12px;
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 150);
        }
    }, 5000);
}

/**
 * Get icon for notification type
 */
function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Initialize responsive handlers
 */
function initializeResponsiveHandlers() {
    // Handle responsive table scrolling indicators
    const tableContainers = document.querySelectorAll('.table-responsive');
    
    tableContainers.forEach(container => {
        const table = container.querySelector('table');
        if (table) {
            // Add scroll indicators
            updateScrollIndicators(container);
            
            container.addEventListener('scroll', () => {
                updateScrollIndicators(container);
            });
        }
    });
    
    // Handle mobile menu interactions
    handleMobileInteractions();
}

/**
 * Update scroll indicators for tables
 */
function updateScrollIndicators(container) {
    const scrollLeft = container.scrollLeft;
    const scrollWidth = container.scrollWidth;
    const clientWidth = container.clientWidth;
    
    // Remove existing indicators
    container.classList.remove('scroll-left', 'scroll-right');
    
    // Add appropriate indicators
    if (scrollLeft > 0) {
        container.classList.add('scroll-left');
    }
    
    if (scrollLeft < scrollWidth - clientWidth - 1) {
        container.classList.add('scroll-right');
    }
}

/**
 * Handle mobile-specific interactions
 */
function handleMobileInteractions() {
    // Improve touch interactions on mobile
    if (window.innerWidth <= 768) {
        // Add touch-friendly hover effects
        const cards = document.querySelectorAll('.metric-card, .status-card, .quick-action-btn');
        
        cards.forEach(card => {
            card.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            });
            
            card.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touch-active');
                }, 150);
            });
        });
    }
}

/**
 * Handle window resize events
 */
window.addEventListener('resize', debounce(() => {
    // Reinitialize responsive handlers
    initializeResponsiveHandlers();
}, 250));

/**
 * Debounce utility function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Utility functions for external use
 */
window.dashboardUtils = {
    showNotification,
    refreshDashboard: handleRefreshDashboard,
    formatNumber
};

/**
 * Global refresh function for backward compatibility
 */
function refreshDashboard() {
    handleRefreshDashboard({ target: document.querySelector('.btn-outline-primary'), preventDefault: () => {} });
}

/**
 * Add CSS for touch interactions
 */
const style = document.createElement('style');
style.textContent = `
    .touch-active {
        transform: scale(0.98) !important;
        transition: transform 0.1s ease !important;
    }
    
    .notification-toast {
        animation: slideInFromRight 0.3s ease-out;
    }
    
    @keyframes slideInFromRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .table-responsive.scroll-left::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 20px;
        background: linear-gradient(to right, rgba(255,255,255,0.8), transparent);
        pointer-events: none;
        z-index: 1;
    }
    
    .table-responsive.scroll-right::after {
        content: '';
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 20px;
        background: linear-gradient(to left, rgba(255,255,255,0.8), transparent);
        pointer-events: none;
        z-index: 1;
    }
    
    .table-responsive {
        position: relative;
    }
`;

document.head.appendChild(style);

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeDashboard,
        showNotification,
        refreshDashboard
    };
}
