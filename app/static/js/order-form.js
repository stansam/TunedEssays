document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeDateTimePicker();
    initializeFileUpload();
    initializeToggleButtons();
    initializeEventListeners();
    
    // Initial setup
    if (backendData.defaultValues.wordCount) {
        updateWordCount();
    }
    
    if (backendData.defaultValues.serviceId && backendData.defaultValues.academicLevelId && backendData.defaultValues.deadlineId) {
        updatePricing();
    }
    
    // Initial progress update
    updateProgress();
    updateInstructionCounter();
    
    // Show welcome message
    showAlert('Welcome! Fill out the form below to place your order.', 'info', 3000);
});

// Safely get backend data with fallbacks
const backendData = {
    services: (() => {
        try {
            return window.servicesData || [];
        } catch (e) {
            console.warn('Services data not available:', e);
            return [];
        }
    })(),
    academicLevels: (() => {
        try {
            return window.academicLevelsData || [];
        } catch (e) {
            console.warn('Academic levels data not available:', e);
            return [];
        }
    })(),
    deadlines: (() => {
        try {
            return window.deadlinesData || [];
        } catch (e) {
            console.warn('Deadlines data not available:', e);
            return [];
        }
    })(),
    defaultValues: {
        serviceId: window.serviceId || null,
        academicLevelId: window.academicLevelId || null,
        deadlineId: window.deadlineId || null,
        wordCount: window.wordCount || null,
        pages: window.pages || null,
        totalPrice: window.totalPrice || null,
        dueDate: window.dueDate || null
    },
    selectedData: {
        service: window.selectedService || null,
        academicLevel: window.selectedAcademicLevel || null,
        deadline: window.selectedDeadline || null
    }
};

let flatpickrInstance;
let selectedFiles = [];
let currentPriceData = null;
let selectedReportOption = 'standard';
let reportPrices = {
    'standard': 9.99,
    'turnitin': 29.99
};

// Initialize all event listeners
function initializeEventListeners() {
    // Form field change events
    document.getElementById('service').addEventListener('change', updatePricing);
    document.getElementById('academic_level').addEventListener('change', updatePricing);
    document.getElementById('word_count').addEventListener('input', updateWordCount);
    document.getElementById('description').addEventListener('input', updateInstructionCounter);
    document.getElementById('orderForm').addEventListener('submit', handleFormSubmission);
    
    // Add progress tracking
    const formFields = document.querySelectorAll('.form-control');
    formFields.forEach(field => {
        field.addEventListener('input', updateProgress);
        field.addEventListener('change', updateProgress);
    });

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit form
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('orderForm').dispatchEvent(new Event('submit'));
        }
    });

    // Auto-save every 30 seconds
    setInterval(autoSave, 30000);
    
    // Try to restore form data
    setTimeout(restoreFormData, 500);
}

// Enhanced alert system
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    const alertId = 'alert_' + Date.now();
    
    const alertHTML = `
        <div class="alert alert-${type}" id="${alertId}">
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button type="button" class="close-btn" onclick="closeAlert('${alertId}')">×</button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHTML);
    
    if (duration > 0) {
        setTimeout(() => closeAlert(alertId), duration);
    }
    
    return alertId;
}

function closeAlert(alertId) {
    const alert = document.getElementById(alertId);
    if (alert) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }
}

// Get CSRF token from various possible sources
function getCsrfToken() {
    // Try to get from meta tag
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }
    
    // Try to get from form field
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    if (csrfInput) {
        return csrfInput.value;
    }
    
    console.warn('No CSRF token found');
    return null;
}

// Initialize datetime picker with minimum date
function initializeDateTimePicker() {
    const now = new Date();
    const minDate = new Date(now.getTime() + (3 * 60 * 60 * 1000)); // Minimum 3 hours from now
    const maxDate = new Date(now.getTime() + (2 * 30 * 24 * 60 * 60 * 1000)); // Max 2 months
    const deadlinePicker = document.getElementById('deadline_picker');
    
    flatpickrInstance = flatpickr(deadlinePicker, {
        enableTime: true,
        dateFormat: "h:i K, M j", // Format: "8:35 AM, Jul 26"
        altInput: true,
        altFormat: "h:i K, M j",
        minDate: minDate,
        maxDate: maxDate,
        defaultDate: backendData.defaultValues.dueDate || minDate, // Set default to minimum allowed time or preset value
        time_24hr: false,
        minuteIncrement: 5,
        allowInput: false,
        onChange: function(selectedDates, dateStr, instance) {
            if (selectedDates.length > 0) {
                // Update the hidden input with ISO string for backend compatibility
                const selectedDate = selectedDates[0];
                deadlinePicker.setAttribute('data-iso', selectedDate.toISOString());
                handleDeadlineChange();
            }
        },
        onReady: function(selectedDates, dateStr, instance) {
            // Add custom buttons to the flatpickr calendar
            addCustomButtons(instance);
            
            // If we have a pre-selected date, trigger change event
            if (selectedDates.length > 0) {
                deadlinePicker.setAttribute('data-iso', selectedDates[0].toISOString());
                handleDeadlineChange();
            }
        }
    });
}

function addCustomButtons(instance) {
    const calendar = instance.calendarContainer;
    
    // Create custom buttons container
    const buttonsContainer = document.createElement('div');
    buttonsContainer.className = 'flatpickr-custom-buttons';
    
    // Define button configurations
    const buttons = [
        { text: '3 Hours', hours: 3 },
        { text: '6 Hours', hours: 6 },
        { text: '12 Hours', hours: 12 },
        { text: '24 Hours', hours: 24 },
        { text: '48 Hours', hours: 48 },
        { text: 'Clear', hours: null, isClear: true }
    ];
    
    // Create buttons
    buttons.forEach(buttonConfig => {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = buttonConfig.text;
        button.className = buttonConfig.isClear ? 'flatpickr-custom-btn clear' : 'flatpickr-custom-btn';
        
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (buttonConfig.isClear) {
                instance.clear();
                // Clear hidden field and hide deadline info
                document.getElementById('deadline').value = '';
                document.getElementById('deadlineInfo').style.display = 'none';
                // Update pricing
                updatePricing();
            } else {
                const now = new Date();
                const targetDate = new Date(now.getTime() + (buttonConfig.hours * 60 * 60 * 1000));
                instance.setDate(targetDate);
            }
        });
        
        buttonsContainer.appendChild(button);
    });
    
    // Insert buttons between calendar and time picker
    const timeContainer = calendar.querySelector('.flatpickr-time');
    if (timeContainer) {
        calendar.insertBefore(buttonsContainer, timeContainer);
    } else {
        calendar.appendChild(buttonsContainer);
    }
}

// Handle deadline selection
function handleDeadlineChange() {
    const deadlinePicker = document.getElementById('deadline_picker');
    const isoDate = deadlinePicker.getAttribute('data-iso');
    if (!isoDate) return;

    const nowUTC = Date.now(); // Get current UTC timestamp
    const selectedDateUTC = new Date(isoDate).getTime();
    const timeDiff = selectedDateUTC - nowUTC;
    const hoursDiff = Math.ceil(timeDiff / (1000 * 60 * 60));
    
    // Find the appropriate deadline category from backend data
    let selectedDeadline = null;
    if (backendData.deadlines && backendData.deadlines.length > 0) {
        const sortedDeadlines = [...backendData.deadlines].sort((a, b) => a.hours - b.hours);
        for (let i = 0; i < sortedDeadlines.length; i++) {
            if (hoursDiff <= sortedDeadlines[i].hours) {
                selectedDeadline = sortedDeadlines[i];
                break;
            }
        }
        
        // If longer than the maximum deadline, use the longest one
        if (!selectedDeadline) {
            selectedDeadline = sortedDeadlines[sortedDeadlines.length - 1];
        }
    }

    if (selectedDeadline) {
        // Update hidden deadline field
        document.getElementById('deadline').value = selectedDeadline.id;
        
        // Show deadline info
        const deadlineInfo = document.getElementById('deadlineInfo');
        const deadlineText = document.getElementById('deadlineText');
        
        const days = Math.floor(hoursDiff / 24);
        const hours = hoursDiff % 24;
        let timeText = '';
        
        if (days > 0) {
            timeText = `${days} day${days > 1 ? 's' : ''}`;
            if (hours > 0) timeText += ` and ${hours} hour${hours > 1 ? 's' : ''}`;
        } else {
            timeText = `${hoursDiff} hour${hoursDiff > 1 ? 's' : ''}`;
        }
        
        deadlineText.textContent = `${timeText} from now.`;
        deadlineInfo.style.display = 'block';
        
        updatePricing();
    }
}

function initializeToggleButtons() {
    const toggleOptions = document.querySelectorAll('.toggle-option');
    
    if (toggleOptions.length === 0) {
        console.warn('No toggle options found - plagiarism report section may not be present');
        return;
    }
    
    toggleOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            toggleOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Get the selected option value
            selectedReportOption = this.getAttribute('data-option');
            console.log('Selected plagiarism report option:', selectedReportOption);
            
            // Update progress tracking
            updateProgress();
            
            // Trigger pricing update
            updatePricing();
        });
    });
    
    // Set initial selection if needed
    const defaultOption = document.querySelector('.toggle-option.selected');
    if (defaultOption) {
        selectedReportOption = defaultOption.getAttribute('data-option');
    }
}

// Fetch pricing from backend API
async function fetchPricing() {
    const service = document.getElementById('service').value;
    const academicLevel = document.getElementById('academic_level').value;
    const wordCount = parseInt(document.getElementById('word_count').value) || 0;
    const deadline = document.getElementById('deadline').value;
    
    if (!service || !academicLevel || !wordCount || !deadline) {
        resetPricingSummary();
        return;
    }

    try {
        // Show loading state
        const pricingSummary = document.querySelector('.pricing-summary');
        pricingSummary.classList.add('loading');
        
        const response = await fetch('/api/calculate-price', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken() || ''
            },
            body: JSON.stringify({
                service_id: parseInt(service),
                academic_level_id: parseInt(academicLevel),
                deadline_id: parseInt(deadline),
                word_count: wordCount
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        currentPriceData = data;
        updatePricingSummary(data);
        
    } catch (error) {
        console.error('Error fetching pricing:', error);
        showAlert(`Failed to calculate pricing: ${error.message}`, 'error');
        resetPricingSummary();
    } finally {
        // Remove loading state
        const pricingSummary = document.querySelector('.pricing-summary');
        pricingSummary.classList.remove('loading');
    }
}

// Update pricing summary display
function updatePricingSummary(data) {
    if (!data) {
        resetPricingSummary();
        return;
    }

    // Update service display
    const serviceSelect = document.getElementById('service');
    const selectedServiceText = serviceSelect.options[serviceSelect.selectedIndex]?.text || '-';
    document.getElementById('selectedService').textContent = selectedServiceText;

    // Update academic level display
    const levelSelect = document.getElementById('academic_level');
    const selectedLevelText = levelSelect.options[levelSelect.selectedIndex]?.text || '-';
    document.getElementById('selectedLevel').textContent = selectedLevelText;

    // Update deadline display
    const deadlineText = document.getElementById('deadlineText').textContent || '-';
    document.getElementById('selectedDeadline').textContent = deadlineText;

    // Update pages display
    document.getElementById('summaryPages').textContent = data.page_count.toFixed(0) || 0;
    
    // Calculate plagiarism report price
    const plagiarismPrice = reportPrices[selectedReportOption] || 0;
    document.getElementById('selectedReport').textContent = `$${plagiarismPrice.toFixed(2)}`;
    
    // Calculate total price
    const totalOrdPrice = plagiarismPrice + data.total_price;
    document.getElementById('totalPrice').textContent = `$${totalOrdPrice.toFixed(2)}`;
}

// Reset pricing summary
function resetPricingSummary() {
    document.getElementById('selectedService').textContent = '-';
    document.getElementById('selectedLevel').textContent = '-';
    document.getElementById('selectedDeadline').textContent = '-';
    document.getElementById('selectedReport').textContent = '$0.00'
    document.getElementById('summaryPages').textContent = '0';
    document.getElementById('totalPrice').textContent = '$0.00';
    currentPriceData = null;
}

// Update pricing when form values change
function updatePricing() {
    setTimeout(fetchPricing, 300); // Debounce
}

// Word count to pages conversion
function updateWordCount() {
    const wordCount = parseInt(document.getElementById('word_count').value) || 0;
    const pages = Math.ceil(wordCount / 275); // 275 words per page
    document.getElementById('pageCount').textContent = pages;
    
    // Update word count status
    const wordCountStatus = document.getElementById('wordCountStatus');
    if (wordCount < 275) {
        wordCountStatus.textContent = 'Minimum 275 words required';
        wordCountStatus.style.color = 'var(--error-color)';
    } else if (wordCount > 50000) {
        wordCountStatus.textContent = 'Maximum 50,000 words allowed';
        wordCountStatus.style.color = 'var(--error-color)';
    } else {
        wordCountStatus.textContent = 'Valid word count';
        wordCountStatus.style.color = 'var(--success-color)';
    }
    
    updatePricing();
}

// File upload handling
function initializeFileUpload() {
    const fileUpload = document.getElementById('fileUpload');
    const fileInput = document.getElementById('files');
    const fileList = document.getElementById('fileList');

    // Click to browse
    fileUpload.addEventListener('click', () => fileInput.click());

    // Drag and drop
    fileUpload.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUpload.classList.add('dragover');
    });

    fileUpload.addEventListener('dragleave', () => {
        fileUpload.classList.remove('dragover');
    });

    fileUpload.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUpload.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

function handleFiles(files) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'];
    
    Array.from(files).forEach(file => {
        // Check file size
        if (file.size > maxSize) {
            showAlert(`File "${file.name}" is too large. Maximum size is 10MB.`, 'error');
            return;
        }

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExtension)) {
            showAlert(`File type "${fileExtension}" is not supported.`, 'error');
            return;
        }

        // Check if file already exists
        if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            showAlert(`File "${file.name}" is already selected.`, 'error');
            return;
        }

        selectedFiles.push(file);
        addFileToList(file);
    });
}

function addFileToList(file) {
    const fileList = document.getElementById('fileList');
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
        <span><i class="fas fa-file"></i> ${file.name} (${formatFileSize(file.size)})</span>
        <button type="button" onclick="removeFile('${file.name}', ${file.size})">Remove</button>
    `;
    fileList.appendChild(fileItem);
}

function removeFile(fileName, fileSize) {
    selectedFiles = selectedFiles.filter(f => !(f.name === fileName && f.size === fileSize));
    
    // Remove from display
    const fileList = document.getElementById('fileList');
    const fileItems = fileList.querySelectorAll('.file-item');
    fileItems.forEach(item => {
        if (item.textContent.includes(fileName)) {
            item.remove();
        }
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Form validation
function validateForm() {
    let isValid = true;

    // Clear previous errors
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');

    // Validate service
    const service = document.getElementById('service').value;
    if (!service) {
        showFieldError('serviceError', 'Please select a service');
        isValid = false;
    }

    // Validate academic level
    const academicLevel = document.getElementById('academic_level').value;
    if (!academicLevel) {
        showFieldError('academicLevelError', 'Please select an academic level');
        isValid = false;
    }

    // Validate deadline
    const deadlinePicker = document.getElementById('deadline_picker').value;
    const deadlineId = document.getElementById('deadline').value;
    if (!deadlinePicker || !deadlineId) {
        showFieldError('deadlineError', 'Please select a deadline');
        isValid = false;
    }

    // Validate word count
    const wordCount = parseInt(document.getElementById('word_count').value) || 0;
    if (wordCount < 275) {
        showFieldError('wordCountError', 'Minimum word count is 275');
        isValid = false;
    } else if (wordCount > 50000) {
        showFieldError('wordCountError', 'Maximum word count is 50,000');
        isValid = false;
    }

    // Validate title
    const title = document.getElementById('title').value.trim();
    if (!title) {
        showFieldError('titleError', 'Please enter a paper title');
        isValid = false;
    }
    
    // Validate plagiarism report
    if (!validatePlagiarismReport()) {
        isValid = false;
    }

    return isValid;
}

function showFieldError(fieldId, message) {
    const errorElement = document.getElementById(fieldId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

// Update progress bar
function updateProgress() {
    const fields = ['service', 'academic_level', 'deadline_picker', 'word_count', 'title'];
    const completed = fields.filter(fieldId => {
        const field = document.getElementById(fieldId);
        return field && field.value.trim() !== '';
    }).length;

    let totalFields = fields.length;
    let completedFields = completed;
    
    const toggleContainer = document.querySelector('.toggle-container');
    if (toggleContainer) {
        totalFields += 1;
        if (selectedReportOption) {
            completedFields += 1;
        }
    }
    
    const progress = (completedFields / totalFields) * 100;
    document.getElementById('progressFill').style.width = progress + '%';
}

// Character counter for instructions
function updateInstructionCounter() {
    const textarea = document.getElementById('description');
    const counter = document.getElementById('instructionCount');
    const length = textarea.value.length;
    counter.textContent = `${length} characters`;
}

function validatePlagiarismReport() {
    // Add plagiarism report validation if needed
    const toggleContainer = document.querySelector('.toggle-container');
    if (toggleContainer) {
        const selectedOption = document.querySelector('.toggle-option.selected');
        if (!selectedOption) {
            showFieldError('plagiarismReportError', 'Please select a plagiarism report option');
            return false;
        }
    }
    return true;
}

// Form submission
async function handleFormSubmission(e) {
    e.preventDefault();
    
    if (!validateForm()) {
        showAlert('Please fix the errors below before submitting', 'error');
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    try {
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        // Create FormData
        const formData = new FormData();
        
        // Add form fields
        const formFields = [
            'service', 'academic_level', 'citation_style', 'deadline',
            'word_count', 'title', 'description'
        ];
        
        formFields.forEach(fieldName => {
            const field = document.getElementById(fieldName);
            if (field && field.value) {
                formData.append(fieldName, field.value);
            }
        });

        // Add deadline picker value for reference
        const deadlinePicker = document.getElementById('deadline_picker');
        if (deadlinePicker.value) {
            formData.append('deadline_picker', deadlinePicker.value);
        }

        // Add files
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        // Add plagiarism report information
        if (selectedReportOption) {
            formData.append('plagiarism_report_type', selectedReportOption);
            formData.append('plagiarism_report_price', reportPrices[selectedReportOption].toString());
        }

        // Submit form
        const response = await fetch(window.location.pathname, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken() || ''
            }
        });

        if (response.ok) {
            // Check if response is JSON or redirect
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const result = await response.json();
                if (result.success) {
                    showAlert('Order submitted successfully!', 'success');
                    // Redirect or handle success
                    if (result.redirect_url) {
                        window.location.href = result.redirect_url;
                    }
                } else {
                    throw new Error(result.message || 'Failed to submit order');
                }
            } else {
                // Handle redirect response
                window.location.href = response.url;
            }
        } else {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
    } catch (error) {
        console.error('Form submission error:', error);
        showAlert(`Failed to submit order: ${error.message}`, 'error');
    } finally {
        // Restore button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// Auto-save functionality
function autoSave() {
    const formData = {
        service: document.getElementById('service').value,
        academic_level: document.getElementById('academic_level').value,
        citation_style: document.getElementById('citation_style').value,
        word_count: document.getElementById('word_count').value,
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        deadline_picker: document.getElementById('deadline_picker').value,
        plagiarism_report_type: selectedReportOption,
        timestamp: Date.now()
    };
    
    // Store in memory (since localStorage is not available)
    window.orderFormData = formData;
}

// Restore form data on page load
function restoreFormData() {
    if (window.orderFormData) {
        const data = window.orderFormData;
        
        // Only restore if data is less than 1 hour old
        if (Date.now() - data.timestamp < 3600000) {
            Object.keys(data).forEach(key => {
                if (key === 'plagiarism_report_type' && data[key]) {
                    // Restore plagiarism report selection
                    selectedReportOption = data[key];
                    const optionToSelect = document.querySelector(`[data-option="${data[key]}"]`);
                    if (optionToSelect) {
                        document.querySelectorAll('.toggle-option').forEach(opt => opt.classList.remove('selected'));
                        optionToSelect.classList.add('selected');
                    }
                } else if (key !== 'timestamp' && key !== 'plagiarism_report_type') {
                    const field = document.getElementById(key);
                    if (field && !field.value) {
                        field.value = data[key];
                    }
                }
            });
            
            showAlert('Form data restored from previous session', 'info', 3000);
        }
    }
}

// Make necessary functions globally available
window.closeAlert = closeAlert;
window.removeFile = removeFile;