let flatpickrInstance;
let currentOrderId;

function initializeFlatpickr() {
    flatpickrInstance = flatpickr("#newDeadline", {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true,
        minDate: "today",
        defaultHour: 12,
        defaultMinute: 0,
        allowInput: true,
        clickOpens: true,
        placeholder: "YYYY-MM-DD HH:MM"
    });
}

/**
 * Format date for display
 */
function formatDateForDisplay(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (error) {
        return dateString;
    }
}

/**
 * Show alert message in modal
 */
function showAlert(message, type = 'danger') {
    const alertContainer = document.getElementById('alertContainer');
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
}

/**
 * Clear alert messages
 */
function clearAlerts() {
    document.getElementById('alertContainer').innerHTML = '';
}

/**
 * Set loading state for submit button
 */
function setLoadingState(loading) {
    const btn = document.getElementById('saveDeadlineBtn');
    if (loading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

function updateDeadline() {
    // Get the button that was clicked to extract data
    const clickedButton = event.target.closest('button');
    const orderId = clickedButton.getAttribute('data-order-id');
    const currentDeadline = clickedButton.getAttribute('data-current-deadline');
    
    if (!orderId) {
        alert('Order ID not found. Please try again.');
        return;
    }
    
    // Store order ID globally
    currentOrderId = orderId;
    
    // Populate the form
    document.getElementById('orderId').value = orderId;
    document.getElementById('currentDeadlineDisplay').textContent = 
        currentDeadline ? formatDateForDisplay(currentDeadline) : 'Not set';
    
    // Clear any previous alerts and form data
    clearAlerts();
    document.getElementById('newDeadline').value = '';
    
    // Initialize or reinitialize Flatpickr
    if (flatpickrInstance) {
        flatpickrInstance.destroy();
    }
    initializeFlatpickr();
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('deadlineModal'));
    modal.show();
}

/**
 * Handle form submission
 */
document.getElementById('deadlineForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const newDeadline = document.getElementById('newDeadline').value;
    const orderId = document.getElementById('orderId').value;
    
    if (!newDeadline.trim()) {
        showAlert('Please select a new deadline.');
        return;
    }
    
    // Clear previous alerts
    clearAlerts();
    setLoadingState(true);
    
    // Convert the date to ISO format for the API
    let isoDeadline;
    try {
        const date = new Date(newDeadline);
        isoDeadline = date.toISOString();
    } catch (error) {
        showAlert('Invalid date format. Please select a valid date and time.');
        setLoadingState(false);
        return;
    }
    
    // Make AJAX request to update deadline
    $.ajax({
        url: `/order-activities/order/${orderId}/deadline`,
        method: 'PUT',
        headers: {
            'X-CSRFToken': document.querySelector("input[name=csrf_token]").value
        },
        contentType: 'application/json',
        data: JSON.stringify({
            deadline: isoDeadline
        }),
        success: function(response) {
            setLoadingState(false);
            
            if (response.success) {
                showAlert('Deadline updated successfully!', 'success');
                
                // Close modal after a short delay
                setTimeout(function() {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('deadlineModal'));
                    modal.hide();
                    
                    // Optionally refresh the page or update the UI
                    // window.location.reload();
                }, 1500);
            } else {
                showAlert(response.error || 'Failed to update deadline. Please try again.');
            }
        },
        error: function(xhr, status, error) {
            setLoadingState(false);
            
            let errorMessage = 'An error occurred while updating the deadline.';
            
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = xhr.responseJSON.error;
            } else if (xhr.status === 404) {
                errorMessage = 'Order not found.';
            } else if (xhr.status === 401) {
                errorMessage = 'You are not authorized to update this order.';
            } else if (xhr.status === 500) {
                errorMessage = 'Server error. Please try again later.';
            }
            
            showAlert(errorMessage);
        }
    });
});

// Initialize Flatpickr when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flatpickr (will be reinitialized when modal opens)
    initializeFlatpickr();
});

// Clean up Flatpickr when modal is hidden
document.getElementById('deadlineModal').addEventListener('hidden.bs.modal', function() {
    if (flatpickrInstance) {
        flatpickrInstance.destroy();
        flatpickrInstance = null;
    }
});