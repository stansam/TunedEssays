class ExtensionNotificationManager {
    constructor() {
        this.floatingIcon = document.getElementById('floatingExtensionIcon');
        this.extensionPopup = document.getElementById('extensionPopup');
        this.popupBackdrop = document.getElementById('popupBackdrop');
        this.closePopupBtn = document.getElementById('closePopupBtn');
        this.acknowledgeBtn = document.getElementById('acknowledgeBtn');
        this.viewFullTicketBtn = document.getElementById('viewFullTicketBtn');
        
        this.orderId = this.getOrderIdFromPage(); // You'll need to implement this
        this.isPopupOpen = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.checkExtensionStatus();
        
        // Check for updates every 30 seconds
        setInterval(() => {
            this.checkExtensionStatus();
        }, 30000);
    }
    
    bindEvents() {
        // Open popup when icon is clicked
        this.floatingIcon.addEventListener('click', () => {
            this.openPopup();
        });
        
        // Close popup events
        this.closePopupBtn.addEventListener('click', () => {
            this.closePopup();
        });
        
        this.popupBackdrop.addEventListener('click', () => {
            this.closePopup();
        });
        
        this.acknowledgeBtn.addEventListener('click', () => {
            this.acknowledgeExtension();
        });
        
        this.viewFullTicketBtn.addEventListener('click', () => {
            this.viewFullTicket();
        });
        
        // Close popup on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isPopupOpen) {
                this.closePopup();
            }
        });
    }
    
    async checkExtensionStatus() {
        if (!this.orderId) return;
        
        try {
            const response = await fetch(`/client/extension-status/${this.orderId}`);
            const result = await response.json();
            
            if (result.success && result.extension_requested) {
                this.showFloatingIcon();
                this.loadExtensionDetails(result);
            } else {
                this.hideFloatingIcon();
            }
        } catch (error) {
            console.error('Error checking extension status:', error);
        }
    }
    
    loadExtensionDetails(data) {
        // Update popup content with extension details
        if (data.extension_requested_at) {
            const date = new Date(data.extension_requested_at);
            document.getElementById('extensionRequestDate').textContent = 
                date.toLocaleDateString() + ' at ' + date.toLocaleTimeString();
        }
        
        if (data.reason) {
            document.getElementById('extensionReason').textContent = data.reason;
        }
        
        // Store ticket ID for "View Full Ticket" functionality
        if (data.ticket_id) {
            this.ticketId = data.ticket_id;
        }
    }
    
    showFloatingIcon() {
        this.floatingIcon.style.display = 'flex';
        
        // Add entrance animation
        setTimeout(() => {
            this.floatingIcon.style.transform = 'scale(1)';
            this.floatingIcon.style.opacity = '1';
        }, 100);
    }
    
    hideFloatingIcon() {
        this.floatingIcon.style.display = 'none';
    }
    
    openPopup() {
        this.isPopupOpen = true;
        this.popupBackdrop.classList.add('show');
        this.extensionPopup.classList.add('show');
        this.floatingIcon.classList.add('popup-open');
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
    
    closePopup() {
        this.isPopupOpen = false;
        this.popupBackdrop.classList.remove('show');
        this.extensionPopup.classList.remove('show');
        this.floatingIcon.classList.remove('popup-open');
        
        // Restore body scroll
        document.body.style.overflow = '';
    }
    
    async acknowledgeExtension() {
        try {
            const response = await fetch('/client/acknowledge-extension', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    order_id: this.orderId
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.closePopup();
                this.hideFloatingIcon();
                this.showToast('Extension request acknowledged', 'success');
            } else {
                this.showToast(result.message || 'Error acknowledging extension', 'error');
            }
        } catch (error) {
            console.error('Error acknowledging extension:', error);
            this.showToast('An error occurred', 'error');
        }
    }
    
    viewFullTicket() {
        if (this.ticketId) {
            // Redirect to support ticket page
            window.location.href = `/support/ticket/${this.ticketId}`;
        } else {
            // Redirect to general support page
            window.location.href = '/support';
        }
    }
    
    getOrderIdFromPage() {
        // Multiple ways to get order ID - adjust based on your page structure
        
        // Method 1: From URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        let orderId = urlParams.get('order_id') || urlParams.get('id');
        
        // Method 2: From URL path (e.g., /order/123/activities)
        if (!orderId) {
            const pathMatch = window.location.pathname.match(/\/order\/(\d+)/);
            if (pathMatch) {
                orderId = pathMatch[1];
            }
        }
        
        // Method 3: From a data attribute on the page
        if (!orderId) {
            const orderElement = document.querySelector('[data-order-id]');
            if (orderElement) {
                orderId = orderElement.getAttribute('data-order-id');
            }
        }
        
        // Method 4: From a global JavaScript variable (if you set one)
        if (!orderId && typeof window.ORDER_ID !== 'undefined') {
            orderId = window.ORDER_ID;
        }
        
        return orderId ? parseInt(orderId) : null;
    }
    
    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        toast.style.cssText = `
            top: 20px; 
            right: 20px; 
            z-index: 9999; 
            min-width: 250px;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => toast.style.opacity = '1', 100);
        
        // Remove toast after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
}

// Initialize the extension notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new ExtensionNotificationManager();
});

// For testing purposes - you can remove this
// Simulate extension request after 3 seconds (for demo)
setTimeout(() => {
    // Uncomment the line below to test the floating icon
    // document.getElementById('floatingExtensionIcon').style.display = 'flex';
}, 3000);