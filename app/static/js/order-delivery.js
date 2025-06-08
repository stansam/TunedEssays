class OrderDeliveryFilesHandler {
    constructor() {
        this.loadedOrders = new Set();
        this.downloadingFiles = new Set();
        this.init();
    }

    init() {
        // Bind event listeners for file toggles
        this.bindFileToggleEvents();
    }

    /**
     * Bind click events to file toggle buttons
     */
    bindFileToggleEvents() {
        $(document).on('click', '[data-bs-toggle="files"]', (e) => {
            e.preventDefault();
            const button = $(e.currentTarget);
            const orderId = button.data('order-id');
            const filesContainer = $(`#filesContainer-${orderId}`);

            if (filesContainer.is(':visible')) {
                this.hideFiles(orderId);
            } else {
                this.showFiles(orderId);
            }
        });
    }

    /**
     * Show files container and load files if not already loaded
     */
    showFiles(orderId) {
        const filesContainer = $(`#filesContainer-${orderId}`);
        const toggleButton = $(`[data-order-id="${orderId}"][data-bs-toggle="files"]`);
        
        filesContainer.slideDown();
        toggleButton.find('i').removeClass('fa-chevron-down').addClass('fa-chevron-up');

        // Load files if not already loaded
        if (!this.loadedOrders.has(orderId)) {
            this.loadOrderFiles(orderId);
        }
    }

    /**
     * Hide files container
     */
    hideFiles(orderId) {
        const filesContainer = $(`#filesContainer-${orderId}`);
        const toggleButton = $(`[data-order-id="${orderId}"][data-bs-toggle="files"]`);
        
        filesContainer.slideUp();
        toggleButton.find('i').removeClass('fa-chevron-up').addClass('fa-chevron-down');
    }

    /**
     * Load delivery files for a specific order
     */
    async loadOrderFiles(orderId) {
        const loadingEl = $(`#filesLoading-${orderId}`);
        const listEl = $(`#filesList-${orderId}`);
        const errorEl = $(`#filesError-${orderId}`);

        try {
            // Show loading state
            loadingEl.show();
            listEl.hide();
            errorEl.hide();

            // Fetch delivery files
            const response = await fetch(`/result-services/orders/${orderId}/delivery-files`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                this.renderDeliveryFiles(orderId, data);
                this.loadedOrders.add(orderId);
            } else {
                throw new Error(data.error || 'Failed to load delivery files');
            }

        } catch (error) {
            console.error('Error loading delivery files:', error);
            this.showError(orderId, error.message);
        } finally {
            loadingEl.hide();
        }
    }

    /**
     * Render delivery files in the UI
     */
    renderDeliveryFiles(orderId, data) {
        const listEl = $(`#filesList-${orderId}`);
        
        if (!data.deliveries || data.deliveries.length === 0) {
            listEl.html(`
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-inbox fa-2x mb-3"></i>
                    <p>No delivery files available for this order.</p>
                </div>
            `);
            listEl.show();
            return;
        }

        let html = '';

        data.deliveries.forEach((delivery, deliveryIndex) => {
            html += `
                <div class="delivery-section mb-4">
                    <div class="delivery-header d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h6 class="mb-1">
                                <i class="fas fa-truck me-2"></i>
                                Delivery #${deliveryIndex + 1}
                                <span class="badge bg-${this.getStatusBadgeColor(delivery.delivery_status)} ms-2">
                                    ${delivery.delivery_status}
                                </span>
                            </h6>
                            <small class="text-muted">
                                Delivered: ${this.formatDateTime(delivery.delivered_at)}
                                ${delivery.has_plagiarism_report ? '<i class="fas fa-shield-alt text-success ms-2" title="Includes plagiarism report"></i>' : ''}
                            </small>
                        </div>
                        ${delivery.files.length > 1 ? `
                            <button class="btn btn-outline-primary btn-sm" onclick="orderFilesHandler.downloadAllFiles(${orderId})">
                                <i class="fas fa-download me-1"></i>
                                Download All
                            </button>
                        ` : ''}
                    </div>
                    
                    <div class="files-grid">
                        ${this.renderFiles(delivery.files)}
                    </div>
                </div>
            `;
        });

        listEl.html(html);
        listEl.show();
    }

    /**
     * Render individual files
     */
    renderFiles(files) {
        return files.map(file => `
            <div class="file-item card border-0 shadow-sm mb-2">
                <div class="card-body p-3">
                    <div class="d-flex align-items-center">
                        <div class="file-icon me-3">
                            <i class="${file.file_icon || this.getFileIcon(file.file_type)} fa-2x text-primary"></i>
                        </div>
                        <div class="file-info flex-grow-1">
                            <h6 class="mb-1">${this.escapeHtml(file.original_filename)}</h6>
                            <div class="file-meta text-muted small">
                                <span class="me-3">
                                    <i class="fas fa-file me-1"></i>
                                    ${file.file_format.toUpperCase()}
                                </span>
                                <span class="me-3">
                                    <i class="fas fa-hdd me-1"></i>
                                    ${file.file_size_mb} MB
                                </span>
                                ${file.is_plagiarism_report ? `
                                    <span class="badge bg-success">
                                        <i class="fas fa-shield-alt me-1"></i>
                                        Plagiarism Report
                                    </span>
                                ` : ''}
                            </div>
                            ${file.description ? `
                                <small class="text-muted d-block mt-1">${this.escapeHtml(file.description)}</small>
                            ` : ''}
                        </div>
                        <div class="file-actions">
                            <button class="btn btn-primary btn-sm" 
                                    onclick="orderFilesHandler.downloadFile(${file.id}, '${this.escapeHtml(file.original_filename)}')"
                                    id="downloadBtn-${file.id}">
                                <i class="fas fa-download me-1"></i>
                                Download
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Download a single file
     */
    async downloadFile(fileId, filename) {
        if (this.downloadingFiles.has(fileId)) {
            return; // Already downloading
        }

        const button = $(`#downloadBtn-${fileId}`);
        const originalHtml = button.html();

        try {
            this.downloadingFiles.add(fileId);
            
            // Update button to show loading state
            button.prop('disabled', true).html(`
                <div class="spinner-border spinner-border-sm me-1" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                Downloading...
            `);

            // Create download link and trigger download
            const downloadUrl = `/result-services/orders/${fileId}/download`;
            
            // Use fetch to check if file exists and handle errors
            const response = await fetch(downloadUrl, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Download failed' }));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            // If successful, create a blob and download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show success feedback
            this.showFileDownloadSuccess(filename);

        } catch (error) {
            console.error('File download error:', error);
            // console.error(`invalid file path: ${filepath}`)
            this.showFileDownloadError(error.message, filename);
        } finally {
            // Reset button state
            button.prop('disabled', false).html(originalHtml);
            this.downloadingFiles.delete(fileId);
        }
    }

    /**
     * Download all files for an order as ZIP
     */
    async downloadAllFiles(orderId) {
        const button = $(`[onclick="orderFilesHandler.downloadAllFiles(${orderId})"]`);
        const originalHtml = button.html();

        try {
            button.prop('disabled', true).html(`
                <div class="spinner-border spinner-border-sm me-1" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                Creating ZIP...
            `);

            const downloadUrl = `/result-services/orders/${orderId}/delivery-files/download-all`;
            
            const response = await fetch(downloadUrl, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'ZIP download failed' }));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            // Get filename from response headers
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `order_${orderId}_files.zip`;
            if (contentDisposition) {
                const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
                if (matches != null && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }

            // Download the ZIP file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            this.showFileDownloadSuccess(`All files (${filename})`);

        } catch (error) {
            console.error('ZIP download error:', error);
            this.showFileDownloadError(error.message, 'ZIP archive');
        } finally {
            button.prop('disabled', false).html(originalHtml);
        }
    }

    /**
     * Show error state
     */
    showError(orderId, message) {
        const errorEl = $(`#filesError-${orderId}`);
        const listEl = $(`#filesList-${orderId}`);
        
        errorEl.find('.alert').html(`
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button class="btn btn-link btn-sm p-0 ms-2" onclick="orderFilesHandler.retryLoadFiles(${orderId})">
                Retry
            </button>
        `);
        
        errorEl.show();
        listEl.hide();
    }

    /**
     * Retry loading files
     */
    retryLoadFiles(orderId) {
        this.loadedOrders.delete(orderId);
        this.loadOrderFiles(orderId);
    }

    /**
     * Show download success notification
     */
    showFileDownloadSuccess(filename) {
        this.showNotification(`Successfully downloaded: ${filename}`, 'success');
    }

    /**
     * Show download error notification
     */
    showFileDownloadError(message, filename) {
        this.showNotification(`Failed to download ${filename}: ${message}`, 'danger');
    }

    /**
     * Show notification (you can customize this based on your notification system)
     */
    showNotification(message, type = 'info') {
        // Using Bootstrap toast if available, otherwise console log
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const toastHtml = `
                <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                    <div class="d-flex">
                        <div class="toast-body">${message}</div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                </div>
            `;
            
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            toastContainer.insertAdjacentHTML('beforeend', toastHtml);
            const toastElement = toastContainer.lastElementChild;
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
            
            // Remove toast element after it's hidden
            toastElement.addEventListener('hidden.bs.toast', () => {
                toastElement.remove();
            });
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Get appropriate status badge color
     */
    getStatusBadgeColor(status) {
        const statusColors = {
            'delivered': 'success',
            'pending': 'warning',
            'failed': 'danger',
            'partial': 'info'
        };
        return statusColors[status.toLowerCase()] || 'secondary';
    }

    /**
     * Get file icon based on file type
     */
    getFileIcon(fileType) {
        const iconMap = {
            'pdf': 'fas fa-file-pdf',
            'doc': 'fas fa-file-word',
            'docx': 'fas fa-file-word',
            'txt': 'fas fa-file-alt',
            'xls': 'fas fa-file-excel',
            'xlsx': 'fas fa-file-excel',
            'ppt': 'fas fa-file-powerpoint',
            'pptx': 'fas fa-file-powerpoint',
            'zip': 'fas fa-file-archive',
            'rar': 'fas fa-file-archive',
            'jpg': 'fas fa-file-image',
            'jpeg': 'fas fa-file-image',
            'png': 'fas fa-file-image',
            'gif': 'fas fa-file-image'
        };
        return iconMap[fileType.toLowerCase()] || 'fas fa-file';
    }

    /**
     * Format datetime string
     */
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
}

// Initialize the handler when document is ready
$(document).ready(function() {
    window.orderFilesHandler = new OrderDeliveryFilesHandler();
});
