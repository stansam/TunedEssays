// // Edit Sample Modal Handler
// document.addEventListener('DOMContentLoaded', function() {
//     const editModal = document.getElementById('editSampleModal');
//     const editForm = document.getElementById('editSampleForm');
//     const editButtons = document.querySelectorAll('[data-bs-target="#editSampleModal"]');
    
//     // Handle edit button clicks
//     editButtons.forEach(button => {
//         button.addEventListener('click', function() {
//             const sampleId = this.getAttribute('data-sample-id');
//             if (sampleId) {
//                 loadSampleForEdit(sampleId);
//             }
//         });
//     });
    
//     // Load sample data for editing
//     function loadSampleForEdit(sampleId) {
//         // Show loading state
//         showEditModalLoading(true);
        
//         fetch(`/admin/samples/edit/${sampleId}`, {
//             method: 'GET',
//             headers: {
//                 'Content-Type': 'application/json',
//                 'X-CSRFToken': document.querySelector('[name=csrf_token]').value
//             }
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 populateEditForm(data.sample);
//                 showEditModalLoading(false);
//             } else {
//                 showToast('Error loading sample: ' + data.message, 'error');
//                 hideModal(editModal);
//             }
//         })
//         .catch(error => {
//             console.error('Error loading sample:', error);
//             showToast('Error loading sample data', 'error');
//             hideModal(editModal);
//         });
//     }
    
//     // Populate form with sample data
//     function populateEditForm(sample) {
//         document.getElementById('edit_sample_id').value = sample.id;
//         document.getElementById('edit_title').value = sample.title || '';
//         document.getElementById('edit_excerpt').value = sample.excerpt || '';
//         document.getElementById('edit_content').value = sample.content || '';
//         document.getElementById('edit_word_count').value = sample.word_count || 0;
//         document.getElementById('edit_featured').checked = sample.featured || false;
        
//         // Set service selection
//         const serviceSelect = document.getElementById('edit_service_id');
//         serviceSelect.value = sample.service_id || '';
        
//         // Trigger Select2 update if you're using Select2
//         if ($(serviceSelect).hasClass('select2')) {
//             $(serviceSelect).trigger('change');
//         }
        
//         // Handle current image preview
//         const currentImagePreview = document.getElementById('current_image_preview');
//         const currentImage = document.getElementById('current_image');
        
//         if (sample.image) {
//             currentImage.src = `/static/uploads/samples/${sample.image}`;
//             currentImagePreview.style.display = 'block';
//         } else {
//             currentImagePreview.style.display = 'none';
//         }
        
//         // Update form action URL
//         editForm.action = `/admin/samples/${sample.id}`;
//     }
    
//     // Handle form submission
//     editForm.addEventListener('submit', function(e) {
//         e.preventDefault();
        
//         const sampleId = document.getElementById('edit_sample_id').value;
//         const formData = new FormData(editForm);
        
//         // Add method override for PUT request
//         formData.append('_method', 'PUT');
        
//         // Show loading state
//         const submitBtn = editForm.querySelector('button[type="submit"]');
//         const originalText = submitBtn.innerHTML;
//         submitBtn.disabled = true;
//         submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Updating...';
        
//         fetch(`/admin/samples/edit/${sampleId}`, {
//             method: 'POST', // Using POST with method override
//             body: formData,
//             headers: {
//                 'X-CSRFToken': document.querySelector('[name=csrf_token]').value
//             }
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 showToast('Sample updated successfully', 'success');
//                 hideModal(editModal);
                
//                 // Refresh the samples table/list
//                 if (typeof refreshSamplesList === 'function') {
//                     refreshSamplesList();
//                 } else {
//                     // Fallback: reload page
//                     setTimeout(() => location.reload(), 1000);
//                 }
//             } else {
//                 showToast('Error updating sample: ' + data.message, 'error');
//             }
//         })
//         .catch(error => {
//             console.error('Error updating sample:', error);
//             showToast('Error updating sample', 'error');
//         })
//         .finally(() => {
//             // Reset button state
//             submitBtn.disabled = false;
//             submitBtn.innerHTML = originalText;
//         });
//     });
    
//     // Show/hide loading state in modal
//     function showEditModalLoading(show) {
//         const modalBody = editModal.querySelector('.modal-body');
//         const loadingOverlay = editModal.querySelector('.loading-overlay');
        
//         if (show) {
//             if (!loadingOverlay) {
//                 const overlay = document.createElement('div');
//                 overlay.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
//                 overlay.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
//                 overlay.style.zIndex = '1000';
//                 overlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
//                 modalBody.style.position = 'relative';
//                 modalBody.appendChild(overlay);
//             }
//         } else {
//             if (loadingOverlay) {
//                 loadingOverlay.remove();
//             }
//         }
//     }
    
//     // Reset form when modal is closed
//     editModal.addEventListener('hidden.bs.modal', function() {
//         editForm.reset();
//         document.getElementById('current_image_preview').style.display = 'none';
        
//         // Reset Select2 if used
//         const serviceSelect = document.getElementById('edit_service_id');
//         if ($(serviceSelect).hasClass('select2')) {
//             $(serviceSelect).val('').trigger('change');
//         }
//     });
    
//     // Image preview functionality
//     const imageInput = document.getElementById('edit_image');
//     if (imageInput) {
//         imageInput.addEventListener('change', function(e) {
//             const file = e.target.files[0];
//             if (file) {
//                 // Validate file type
//                 const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
//                 if (!allowedTypes.includes(file.type)) {
//                     showToast('Please select a valid image file (JPEG, PNG, GIF, or WebP)', 'error');
//                     this.value = '';
//                     return;
//                 }
                
//                 // Validate file size (5MB limit)
//                 const maxSize = 5 * 1024 * 1024; // 5MB
//                 if (file.size > maxSize) {
//                     showToast('Image file size must be less than 5MB', 'error');
//                     this.value = '';
//                     return;
//                 }
                
//                 // Show preview
//                 const reader = new FileReader();
//                 reader.onload = function(e) {
//                     const currentImage = document.getElementById('current_image');
//                     const currentImagePreview = document.getElementById('current_image_preview');
//                     currentImage.src = e.target.result;
//                     currentImagePreview.style.display = 'block';
//                 };
//                 reader.readAsDataURL(file);
//             }
//         });
//     }
    
//     // Auto-calculate word count when content changes
//     const contentTextarea = document.getElementById('edit_content');
//     const wordCountInput = document.getElementById('edit_word_count');
    
//     if (contentTextarea && wordCountInput) {
//         contentTextarea.addEventListener('input', function() {
//             const content = this.value.trim();
//             const wordCount = content ? content.split(/\s+/).length : 0;
//             wordCountInput.value = wordCount;
//         });
//     }
// });

// // Utility functions
// function hideModal(modal) {
//     const bsModal = bootstrap.Modal.getInstance(modal);
//     if (bsModal) {
//         bsModal.hide();
//     }
// }

// function showToast(message, type = 'info') {
//     // Assuming you have a toast system in place
//     // Replace with your actual toast implementation
//     if (typeof Toastify !== 'undefined') {
//         Toastify({
//             text: message,
//             duration: 3000,
//             gravity: "top",
//             position: "right",
//             backgroundColor: type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'
//         }).showToast();
//     } else {
//         // Fallback to alert
//         alert(message);
//     }
// }

// // Function to refresh samples list (implement based on your table structure)
// function refreshSamplesList() {
//     // If you're using DataTables
//     if (typeof samplesTable !== 'undefined' && samplesTable.ajax) {
//         samplesTable.ajax.reload(null, false);
//         return;
//     }
    
//     // If you're using a custom function to load samples
//     if (typeof loadSamples === 'function') {
//         loadSamples();
//         return;
//     }
    
//     // Fallback: reload the page
//     location.reload();
// }
// Edit Sample Modal Handler
document.addEventListener('DOMContentLoaded', function() {
    const editModal = document.getElementById('editSampleModal');
    const editForm = document.getElementById('editSampleForm');
    const editButtons = document.querySelectorAll('[data-bs-target="#editSampleModal"]');
    
    // Initialize Quill editor
    let editContentQuill = null;
    
    // Initialize Quill when modal is shown
    editModal.addEventListener('shown.bs.modal', function() {
        if (!editContentQuill) {
            initializeQuillEditor();
        }
    });
    
    
    // Initialize Quill Rich Text Editor
    function initializeQuillEditor() {
        const editorElement = document.getElementById('edit_content_editor');
        
        // Check if element exists and Quill is available
        if (!editorElement) {
            console.error('Quill editor element not found');
            return;
        }
        
        if (typeof Quill === 'undefined') {
            console.error('Quill library not loaded');
            return;
        }
        
        // Destroy existing instance if it exists
        if (editContentQuill) {
            try {
                delete editContentQuill;
            } catch (e) {
                console.warn('Error destroying existing Quill instance:', e);
            }
        }
        const toolbarOptions = [
            ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
            ['blockquote', 'code-block'],
            
            [{ 'header': 1 }, { 'header': 2 }],               // custom button values
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'script': 'sub'}, { 'script': 'super' }],      // superscript/subscript
            [{ 'indent': '-1'}, { 'indent': '+1' }],          // outdent/indent
            [{ 'direction': 'rtl' }],                         // text direction
            
            [{ 'size': ['small', false, 'large', 'huge'] }],  // custom dropdown
            [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
            
            [{ 'color': [] }, { 'background': [] }],          // dropdown with defaults from theme
            [{ 'font': [] }],
            [{ 'align': [] }],
            
            ['link', 'image', 'video'],
            ['clean']                                         // remove formatting button
        ];
        try {
            editContentQuill = new Quill('#edit_content_editor', {
                modules: {
                    toolbar: toolbarOptions
                },
                theme: 'snow',
                placeholder: 'Write your sample content here...'
            });
            
            // Update hidden textarea when content changes
            editContentQuill.on('text-change', function() {
                try{    
                    const html = editContentQuill.root.innerHTML;
                    const hiddenTextarea = document.getElementById('edit_content'); //.value = html
                    if(hiddenTextarea){
                        hiddenTextarea.value = html;
                    }
                    
                    // Auto-update word count
                    updateWordCountFromQuill();
                } catch(error){
                    console.warn('Error updating content from Quill:', error);
                }
            });
            console.log('Quill editor Initiallized Successfully');
        }catch(error){
            console.log('Error updating content from quill:', error);
            const hiddenTextarea = document.getElementById('edit_content');
            if (hiddenTextarea) {
                hiddenTextarea.classList.remove('d-none');
                hiddenTextarea.style.height = '300px';
            }
        }
    }
    
    // Update word count from Quill content
    function updateWordCountFromQuill() {
        if (editContentQuill && typeof editContentQuill.getText === 'function') {
            try{
                const text = editContentQuill.getText().trim();
                const wordCount = text ? text.split(/\s+/).length : 0;
                const wordCountInput = document.getElementById('edit_word_count');
                if (wordCountInput) {
                    wordCountInput.value = wordCount;
                }
            }catch(error){
                console.warn("Error Updating word count from Quill:", error);
            }
        }
    }
    // Handle edit button clicks
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sampleId = this.getAttribute('data-sample-id');
            if (sampleId) {
                loadSampleForEdit(sampleId);
            }
        });
    });
    
    document.addEventListener('openEditSample', function(event) {
        const sampleId = event.detail.sampleId;
        
        // Wait a moment for the preview modal to fully close
        setTimeout(() => {
            // Load sample for editing
            loadSampleForEdit(sampleId);
            
            // Show edit modal
            const editModal = document.getElementById('editSampleModal');
            const editModalInstance = new bootstrap.Modal(editModal);
            editModalInstance.show();
        }, 300);
    });
    
    // Load sample data for editing
    function loadSampleForEdit(sampleId) {
        // Show loading state
        showEditModalLoading(true);
        
        fetch(`/admin/samples/edit/${sampleId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrf_token]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateEditForm(data.sample);
                showEditModalLoading(false);
            } else {
                showToast('Error loading sample: ' + data.message, 'error');
                hideModal(editModal);
            }
        })
        .catch(error => {
            console.error('Error loading sample:', error);
            showToast('Error loading sample data', 'error');
            hideModal(editModal);
        });
    }
    
    // Populate form with sample data
    function populateEditForm(sample) {
        document.getElementById('edit_sample_id').value = sample.id;
        document.getElementById('edit_title').value = sample.title || '';
        document.getElementById('edit_excerpt').value = sample.excerpt || '';
        document.getElementById('edit_word_count').value = sample.word_count || 0;
        document.getElementById('edit_featured').checked = sample.featured || false;
        
        // Set content in Quill editor
        // if (editContentQuill) {
        //     const content = sample.content || '';
        //     editContentQuill.root.innerHTML = content;
        //     // Also update the hidden textarea
        //     document.getElementById('edit_content').value = content;
        // }
        
        const content = sample.content || '';
        const hiddenTextarea = document.getElementById('edit_content');
        
        if (editContentQuill && editContentQuill.root) {
            try {
                editContentQuill.root.innerHTML = content;
                // Also update the hidden textarea
                if (hiddenTextarea) {
                    hiddenTextarea.value = content;
                }
            } catch (error) {
                console.warn('Error setting Quill content:', error);
                // Fallback to textarea
                if (hiddenTextarea) {
                    hiddenTextarea.value = content;
                }
            }
        } else {
            // If Quill isn't ready, just set the textarea
            if (hiddenTextarea) {
                hiddenTextarea.value = content;
            }
            
            // Try to set Quill content after a delay
            setTimeout(() => {
                if (editContentQuill && editContentQuill.root) {
                    try {
                        editContentQuill.root.innerHTML = content;
                    } catch (error) {
                        console.warn('Delayed Quill content setting failed:', error);
                    }
                }
            }, 500);
        }

        // Set service selection
        const serviceSelect = document.getElementById('edit_service_id');
        serviceSelect.value = sample.service_id || '';
        
        // Trigger Select2 update if you're using Select2
        if ($(serviceSelect).hasClass('select2')) {
            $(serviceSelect).trigger('change');
        }
        
        // Handle current image preview
        const currentImagePreview = document.getElementById('current_image_preview');
        const currentImage = document.getElementById('current_image');
        
        if (sample.image) {
            currentImage.src = `/static/uploads/samples/${sample.image}`;
            currentImagePreview.style.display = 'block';
        } else {
            currentImagePreview.style.display = 'none';
        }
        
        // Update form action URL
        editForm.action = `/admin/samples/edit/${sample.id}`;
    }
    
    // Handle form submission
    editForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Update hidden textarea with Quill content before submission
        // if (editContentQuill) {
        //     const html = editContentQuill.root.innerHTML;
        //     document.getElementById('edit_content').value = html;
        // }

        if (editContentQuill && editContentQuill.root) {
            try {
                const html = editContentQuill.root.innerHTML;
                document.getElementById('edit_content').value = html;
            } catch (error) {
                console.warn('Could not get Quill content, using textarea value:', error);
                // Fallback to textarea value if Quill fails
            }
        }
        
        const sampleId = document.getElementById('edit_sample_id').value;
        const formData = new FormData(editForm);
        
        // Add method override for PUT request
        formData.append('_method', 'PUT');
        
        // Show loading state
        const submitBtn = editForm.querySelector('button[type="submit"]');
        // const originalText = submitBtn.innerHTML;
        // submitBtn.disabled = true;
        // submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Updating...';
        let originalText = '';
    
        if (submitBtn) {
            originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Updating...';
        } else {
            console.warn('Submit button not found in form');
        }
        
        fetch(`/admin/samples/edit/${sampleId}`, {
            method: 'POST', // Using POST with method override
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrf_token]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Sample updated successfully', 'success');
                hideModal(editModal);
                
                // Refresh the samples table/list
                if (typeof refreshSamplesList === 'function') {
                    refreshSamplesList();
                } else {
                    // Fallback: reload page
                    setTimeout(() => location.reload(), 1000);
                }
            } else {
                showToast('Error updating sample: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error updating sample:', error);
            showToast('Error updating sample', 'error');
        })
        .finally(() => {
            // Reset button state
            // submitBtn.disabled = false;
            // submitBtn.innerHTML = originalText;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    });
    
    // Show/hide loading state in modal
    function showEditModalLoading(show) {
        const modalBody = editModal.querySelector('.modal-body');
        const loadingOverlay = editModal.querySelector('.loading-overlay');
        
        if (show) {
            if (!loadingOverlay) {
                const overlay = document.createElement('div');
                overlay.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
                overlay.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
                overlay.style.zIndex = '1000';
                overlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
                modalBody.style.position = 'relative';
                modalBody.appendChild(overlay);
            }
        } else {
            if (loadingOverlay) {
                loadingOverlay.remove();
            }
        }
    }
    
    // Reset form when modal is closed
    editModal.addEventListener('hidden.bs.modal', function() {
        editForm.reset();
        document.getElementById('current_image_preview').style.display = 'none';
        
        // Clear Quill editor content
        if (editContentQuill) {
            editContentQuill.setText('');
        }
        
        // Reset Select2 if used
        const serviceSelect = document.getElementById('edit_service_id');
        if ($(serviceSelect).hasClass('select2')) {
            $(serviceSelect).val('').trigger('change');
        }
    });
    
    // Image preview functionality
    const imageInput = document.getElementById('edit_image');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
                if (!allowedTypes.includes(file.type)) {
                    showToast('Please select a valid image file (JPEG, PNG, GIF, or WebP)', 'error');
                    this.value = '';
                    return;
                }
                
                // Validate file size (5MB limit)
                const maxSize = 5 * 1024 * 1024; // 5MB
                if (file.size > maxSize) {
                    showToast('Image file size must be less than 5MB', 'error');
                    this.value = '';
                    return;
                }
                
                // Show preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    const currentImage = document.getElementById('current_image');
                    const currentImagePreview = document.getElementById('current_image_preview');
                    currentImage.src = e.target.result;
                    currentImagePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Auto-calculate word count when content changes - Now handled by Quill
    // Remove the old textarea event listener since we're using Quill's text-change event
});

// Utility functions
function hideModal(modal) {
    const bsModal = bootstrap.Modal.getInstance(modal);
    if (bsModal) {
        bsModal.hide();
    }
}

function showToast(message, type = 'info') {
    // Assuming you have a toast system in place
    // Replace with your actual toast implementation
    if (typeof Toastify !== 'undefined') {
        Toastify({
            text: message,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'
        }).showToast();
    } else {
        // Fallback to alert
        alert(message);
    }
}

// Function to refresh samples list (implement based on your table structure)
function refreshSamplesList() {
    // If you're using DataTables
    if (typeof samplesTable !== 'undefined' && samplesTable.ajax) {
        samplesTable.ajax.reload(null, false);
        return;
    }
    
    // If you're using a custom function to load samples
    if (typeof loadSamples === 'function') {
        loadSamples();
        return;
    }
    
    // Fallback: reload the page
    location.reload();
}