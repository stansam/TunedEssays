// Initialization script for order form
document.addEventListener('DOMContentLoaded', function() {
    // Check if we need to initialize the form
    if (!document.getElementById('orderForm')) {
        console.warn('Order form not found in the document');
        return;
    }
    
    // Process server-side data to make it available to the form scripts
    initializeServerData();
});

// Process server-side data and make it available to the client
function initializeServerData() {
    // Extract data from server-side variables injected into the page
    try {
        // Services
        window.servicesData = typeof services !== 'undefined' ? 
            JSON.parse(decodeHTMLEntities(services)) : [];
            
        // Academic levels
        window.academicLevelsData = typeof academic_levels !== 'undefined' ? 
            JSON.parse(decodeHTMLEntities(academic_levels)) : [];
            
        // Deadlines
        window.deadlinesData = typeof deadlines !== 'undefined' ? 
            JSON.parse(decodeHTMLEntities(deadlines)) : [];
            
        // Selected values
        window.selectedService = typeof selected_service !== 'undefined' ? 
            JSON.parse(decodeHTMLEntities(selected_service)) : null;
            
        window.selectedAcademicLevel = typeof selected_academic_level !== 'undefined' ? 
            JSON.parse(decodeHTMLEntities(selected_academic_level)) : null;
            
        window.selectedDeadline = typeof selected_deadline !== 'undefined' ? 
            JSON.parse(decodeHTMLEntities(selected_deadline)) : null;
            
        // Default values
        window.serviceId = window.selectedService ? window.selectedService.id : null;
        window.academicLevelId = window.selectedAcademicLevel ? window.selectedAcademicLevel.id : null;
        window.deadlineId = window.selectedDeadline ? window.selectedDeadline.id : null;
        
        window.wordCount = typeof word_count !== 'undefined' ? word_count : null;
        window.pages = typeof pages !== 'undefined' ? pages : null;
        window.totalPrice = typeof total_price !== 'undefined' ? total_price : null;
        window.dueDate = typeof due_date !== 'undefined' ? due_date : null;
        
        console.log('Server data initialized successfully', {
            services: window.servicesData,
            academicLevels: window.academicLevelsData,
            deadlines: window.deadlinesData,
            selectedService: window.selectedService,
            selectedAcademicLevel: window.selectedAcademicLevel,
            selectedDeadline: window.selectedDeadline
        });
    } catch (error) {
        console.error('Error initializing server data:', error);
    }
}

// Helper function to decode HTML entities in JSON strings
function decodeHTMLEntities(text) {
    if (!text) return '';
    
    const textArea = document.createElement('textarea');
    textArea.innerHTML = text;
    return textArea.value;
}