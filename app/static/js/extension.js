document.addEventListener('DOMContentLoaded', function() {
    const requestExtensionBtn = document.getElementById('requestExtensionBtn');
    const deadlineExtensionModal = new bootstrap.Modal(document.getElementById('deadlineExtensionModal'));
    const deadlineExtensionForm = document.getElementById('deadlineExtensionForm');
    const submitExtensionBtn = document.getElementById('submitExtensionBtn');
    const orderIdInput = document.getElementById('orderIdInput');
    const extensionDescription = document.getElementById('extensionDescription');
    
    // Open modal when button is clicked
    requestExtensionBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        const orderId = this.getAttribute('data-order-id');
        if (!orderId) {
            showToast('Error', 'Order ID not found', 'error');
            return;
        }
        
        // Check if extension is already requested
        checkExtensionStatus(orderId, function(alreadyRequested) {
            if (alreadyRequested) {
                showToast('Warning', 'Deadline extension has already been requested for this order', 'warning');
                return;
            }
            
            // Set order ID in hidden field
            orderIdInput.value = orderId;
            
            // Clear form
            extensionDescription.value = '';
            
            // Show modal
            deadlineExtensionModal.show();
        });
    });
    
    // Handle form submission
    deadlineExtensionForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = {
            order_id: parseInt(formData.get('order_id')),
            description: formData.get('description').trim()
        };
        
        // Validate
        if (!data.description) {
            showToast('Error', 'Please provide a reason for the deadline extension', 'error');
            return;
        }
        
        // Disable submit button
        submitExtensionBtn.disabled = true;
        submitExtensionBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';
        
        // Submit request
        fetch('/admin/request-deadline-extension', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector("input[name=csrf_token]").value
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showToast('Success', result.message, 'success');
                deadlineExtensionModal.hide();
                
                // Update button state
                updateButtonState(true);
                
                // Optionally refresh the page or update UI
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                showToast('Error', result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error', 'An unexpected error occurred. Please try again.', 'error');
        })
        .finally(() => {
            // Re-enable submit button
            submitExtensionBtn.disabled = false;
            submitExtensionBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit Request';
        });
    });
    
    // Function to check extension status
    function checkExtensionStatus(orderId, callback) {
        fetch(`/admin/get-extension-status/${orderId}`)
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    callback(result.extension_requested);
                } else {
                    callback(false);
                }
            })
            .catch(error => {
                console.error('Error checking extension status:', error);
                callback(false);
            });
    }
    
    // Function to update button state
    function updateButtonState(extensionRequested) {
        if (extensionRequested) {
            requestExtensionBtn.innerHTML = '<i class="fas fa-check me-2"></i>Extension Requested';
            requestExtensionBtn.classList.remove('btn-outline-primary');
            requestExtensionBtn.classList.add('btn-success');
            requestExtensionBtn.disabled = true;
        }
    }
    
    // Function to show toast notifications
    function showToast(title, message, type = 'info') {
        const toastElement = document.getElementById('alertToast');
        const toastTitle = document.getElementById('toastTitle');
        const toastMessage = document.getElementById('toastMessage');
        const toast = new bootstrap.Toast(toastElement);
        
        // Set content
        toastTitle.textContent = title;
        toastMessage.textContent = message;
        
        // Set color based on type
        toastElement.className = 'toast';
        if (type === 'success') {
            toastElement.classList.add('bg-success', 'text-white');
        } else if (type === 'error') {
            toastElement.classList.add('bg-danger', 'text-white');
        } else if (type === 'warning') {
            toastElement.classList.add('bg-warning', 'text-dark');
        } else {
            toastElement.classList.add('bg-info', 'text-white');
        }
        
        // Show toast
        toast.show();
    }
    
    // Check initial extension status when page loads
    const orderId = requestExtensionBtn.getAttribute('data-order-id');
    if (orderId) {
        checkExtensionStatus(orderId, function(alreadyRequested) {
            updateButtonState(alreadyRequested);
        });
    }
});
