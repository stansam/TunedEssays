// Add this to your existing JavaScript in the template
document.addEventListener('DOMContentLoaded', function() {
    // ... your existing code ...
    
    // Category management functionality
    const addCategoryForm = document.getElementById('addCategoryForm');
    const categoryNameInput = document.getElementById('categoryName');
    const saveCategoryBtn = document.getElementById('saveCategoryBtn');
    const categoryErrorAlert = document.getElementById('categoryErrorAlert');
    const categoryErrorMessage = document.getElementById('categoryErrorMessage');
    const categorySelect = document.querySelector('.category-select');
    
    // Handle category form submission
    addCategoryForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Hide any previous error messages
        hideErrorAlert();
        
        // Show loading state
        showLoadingState();
        
        // Get form data
        const formData = new FormData(this);
        const categoryData = {
            name: formData.get('name').trim(),
            description: formData.get('description').trim()
        };
        
        // Basic client-side validation
        if (!categoryData.name) {
            showErrorAlert('Category name is required.');
            hideLoadingState();
            return;
        }
        
        // Submit to backend
        fetch('/admin/blog/categories/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(categoryData)
        })
        .then(response => response.json())
        .then(data => {
            hideLoadingState();
            
            if (data.success) {
                // Add new category to select dropdown
                addCategoryToSelect(data.category);
                
                // Reset form and close modal
                addCategoryForm.reset();
                const modal = bootstrap.Modal.getInstance(document.getElementById('addCategoryModal'));
                modal.hide();
                
                // Show success message
                showSuccessToast('Category created successfully!');
            } else {
                showErrorAlert(data.message || 'Failed to create category.');
            }
        })
        .catch(error => {
            hideLoadingState();
            console.error('Error creating category:', error);
            showErrorAlert('An error occurred while creating the category.');
        });
    });
    
    // Reset form when modal is hidden
    document.getElementById('addCategoryModal').addEventListener('hidden.bs.modal', function() {
        addCategoryForm.reset();
        hideErrorAlert();
        hideLoadingState();
    });
    
    // Helper functions
    function showLoadingState() {
        const btnText = saveCategoryBtn.querySelector('.btn-text');
        const btnLoading = saveCategoryBtn.querySelector('.btn-loading');
        
        btnText.classList.add('d-none');
        btnLoading.classList.remove('d-none');
        saveCategoryBtn.disabled = true;
    }
    
    function hideLoadingState() {
        const btnText = saveCategoryBtn.querySelector('.btn-text');
        const btnLoading = saveCategoryBtn.querySelector('.btn-loading');
        
        btnText.classList.remove('d-none');
        btnLoading.classList.add('d-none');
        saveCategoryBtn.disabled = false;
    }
    
    function showErrorAlert(message) {
        categoryErrorMessage.textContent = message;
        categoryErrorAlert.classList.remove('d-none');
    }
    
    function hideErrorAlert() {
        categoryErrorAlert.classList.add('d-none');
    }
    
    function addCategoryToSelect(category) {
        // Add to native select
        const option = new Option(category.name, category.id);
        categorySelect.add(option);
        
        // If using Select2, refresh it
        if ($(categorySelect).hasClass('select2-hidden-accessible')) {
            $(categorySelect).append(new Option(category.name, category.id, false, false)).trigger('change');
        }
    }
    
    function getCSRFToken() {
        // Get CSRF token from meta tag or form
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }
        
        // Fallback: get from existing form
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        return csrfInput ? csrfInput.value : '';
    }
    
    function showSuccessToast(message) {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
});