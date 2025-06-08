class AdditionalFilesUploader {
    constructor() {
        this.selectedFiles = [];
        this.deliveryId = null;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');

        // Upload area click
        uploadArea.addEventListener('click', () => fileInput.click());

        // File input change
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files));

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files);
        });

        // Upload button
        uploadBtn.addEventListener('click', () => this.uploadFiles());

        // Modal reset on close
        document.getElementById('additionalFilesModal').addEventListener('hidden.bs.modal', () => {
            this.resetForm();
        });
    }

    handleFileSelect(files) {
        Array.from(files).forEach(file => {
            if (this.validateFile(file)) {
                this.selectedFiles.push(file);
            }
        });
        this.updateFileList();
        this.clearAlerts();
    }

    validateFile(file) {
        const allowedTypes = ['pdf', 'docx', 'doc', 'txt', 'zip', 'rar'];
        const maxSize = 16 * 1024 * 1024; // 16MB

        const extension = file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(extension)) {
            this.showAlert(`File "${file.name}" has an invalid format. Allowed formats: ${allowedTypes.join(', ').toUpperCase()}`, 'warning');
            return false;
        }

        if (file.size > maxSize) {
            this.showAlert(`File "${file.name}" exceeds the maximum size limit of 16MB`, 'warning');
            return false;
        }

        if (file.size === 0) {
            this.showAlert(`File "${file.name}" is empty`, 'warning');
            return false;
        }

        // Check for duplicates
        const isDuplicate = this.selectedFiles.some(existingFile => 
            existingFile.name === file.name && existingFile.size === file.size
        );

        if (isDuplicate) {
            this.showAlert(`File "${file.name}" is already selected`, 'info');
            return false;
        }

        return true;
    }

    updateFileList() {
        const fileListContainer = document.getElementById('fileListContainer');
        const fileList = document.getElementById('fileList');

        if (this.selectedFiles.length === 0) {
            fileListContainer.style.display = 'none';
            return;
        }

        fileListContainer.style.display = 'block';
        fileList.innerHTML = '';

        this.selectedFiles.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            fileList.appendChild(fileItem);
        });
    }

    createFileItem(file, index) {
        const div = document.createElement('div');
        div.className = 'file-item';
        
        const extension = file.name.split('.').pop().toLowerCase();
        const iconClass = this.getFileIcon(extension);
        const fileSize = this.formatFileSize(file.size);

        div.innerHTML = `
            <div class="file-info">
                <div class="file-icon">
                    <i class="${iconClass}"></i>
                </div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
            </div>
            <button type="button" class="remove-file" onclick="uploader.removeFile(${index})" title="Remove file">
                <i class="fas fa-times"></i>
            </button>
        `;

        return div;
    }

    getFileIcon(extension) {
        const icons = {
            'pdf': 'fas fa-file-pdf text-danger',
            'docx': 'fas fa-file-word text-primary',
            'doc': 'fas fa-file-word text-primary',
            'txt': 'fas fa-file-alt text-secondary',
            'zip': 'fas fa-file-archive text-warning',
            'rar': 'fas fa-file-archive text-warning'
        };
        return icons[extension] || 'fas fa-file text-secondary';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
        this.clearAlerts();
    }

    async uploadFiles() {
        if (!this.deliveryId) {
            this.showAlert('No delivery ID specified', 'error');
            return;
        }

        if (this.selectedFiles.length === 0) {
            this.showAlert('Please select at least one file', 'warning');
            return;
        }

        const uploadBtn = document.getElementById('uploadBtn');
        const uploadProgress = document.getElementById('uploadProgress');
        const progressBar = uploadProgress.querySelector('.progress-bar');
        const progressText = document.getElementById('progressText');

        // Disable upload button and show progress
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
        uploadProgress.style.display = 'block';
        this.clearAlerts();

        try {
            const formData = new FormData();
            
            // Add files
            this.selectedFiles.forEach(file => {
                formData.append('files', file);
            });

            // Add form data
            formData.append('file_type', document.getElementById('fileType').value);
            formData.append('description', document.getElementById('fileDescription').value);

            // Upload with progress
            const response = await this.uploadWithProgress(formData, progressBar, progressText);
            const result = JSON.parse(xhr.responseText);//await response.json();

            if (result.success) {
                this.showAlert(result.message, 'success');
                
                // Show uploaded files info
                if (result.uploaded_files && result.uploaded_files.length > 0) {
                    let filesList = result.uploaded_files.map(file => 
                        `${file.filename} (${file.size}MB)`
                    ).join(', ');
                    this.showAlert(`Uploaded files: ${filesList}`, 'info');
                }

                // Show errors if any
                if (result.errors && result.errors.length > 0) {
                    result.errors.forEach(error => {
                        this.showAlert(error, 'warning');
                    });
                }

                // Reset form after successful upload
                setTimeout(() => {
                    this.resetForm();
                    bootstrap.Modal.getInstance(document.getElementById('additionalFilesModal')).hide();
                }, 2000);

            } else {
                this.showAlert(result.message || 'Upload failed', 'error');
                
                // Show individual errors
                if (result.errors && result.errors.length > 0) {
                    result.errors.forEach(error => {
                        this.showAlert(error, 'warning');
                    });
                }
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.showAlert('An unexpected error occurred during upload', 'error');
        } finally {
            // Re-enable upload button and hide progress
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Upload Files';
            uploadProgress.style.display = 'none';
        }
    }

    uploadWithProgress(formData, progressBar, progressText) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    progressText.textContent = `Uploading... ${Math.round(percentComplete)}%`;
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr);
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Network error occurred'));
            });
            const orderId = this.deliveryId
            xhr.open('POST', `/admin/delivery/${orderId}/upload-additional-files`);
            xhr.setRequestHeader('X-CSRFToken', document.querySelector('input[name="csrf_token"]').value);
            xhr.send(formData);
        });
    }

    showAlert(message, type) {
        const alertContainer = document.getElementById('alertContainer');
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger', 
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertIcon = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        }[type] || 'fa-info-circle';

        const alert = document.createElement('div');
        alert.className = `alert ${alertClass} d-flex align-items-center`;
        alert.innerHTML = `
            <i class="fas ${alertIcon} me-2"></i>
            <div>${message}</div>
        `;

        alertContainer.appendChild(alert);

        // Auto-remove success and info alerts after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        }
    }

    clearAlerts() {
        document.getElementById('alertContainer').innerHTML = '';
    }

    resetForm() {
        this.selectedFiles = [];
        this.updateFileList();
        document.getElementById('additionalFilesForm').reset();
        document.getElementById('uploadProgress').style.display = 'none';
        this.clearAlerts();
    }

    setDeliveryId(id) {
        this.deliveryId = id;
    }
}

// Initialize the uploader
const uploader = new AdditionalFilesUploader();

// Function to set delivery ID (call this when opening the modal)
function setDeliveryId(deliveryId) {
    uploader.setDeliveryId(deliveryId);
}
