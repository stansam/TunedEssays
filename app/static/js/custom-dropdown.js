document.addEventListener('DOMContentLoaded', function() {
    // Constants for pricing - these will be overridden by API data when available
    let PRICES = {
        'writing': 13,
        'proofreading': 8,
        'technical': 20
    };

    // Elements
    const tabButtons = document.querySelectorAll('.tab-button');
    const serviceTitle = document.querySelector('.service-title');
    const selectInput = document.querySelector('.select-input');
    const mastersSelect = document.querySelector('.masters-select');
    const pageCounter = document.querySelector('.page-counter');
    const counterDisplay = document.querySelector('.counter-display');
    const decrementButton = document.querySelectorAll('.counter-button')[0];
    const incrementButton = document.querySelectorAll('.counter-button')[1];
    const searchInput = document.querySelector('.search-input');
    const mobileSearchInput = document.querySelector('.mobile-search-input');
    const continueButton = document.querySelector('.continue-button');
    const datePicker = document.querySelector('.date-picker');
    
    // Create price section
    const priceSection = document.createElement('div');
    priceSection.className = 'price-section';
    priceSection.innerHTML = `
        <span class="price-label">Approximate Price:</span>
        <span class="price-value">$${PRICES.writing}</span>
    `;
    
    // Insert price section before continue button
    continueButton.parentNode.insertBefore(priceSection, continueButton);
    
    // Variables
    let currentTab = 'writing';
    let pageCount = 1;
    let services = {};
    let academicLevels = {};
    let deadlines = {};
    let selectedServiceId = null;
    let selectedAcademicLevelId = null;
    let selectedDeadlineId = null;
    
    // Fetch data from API
    async function fetchData() {
        try {
            // Fetch categories to get service options for each tab
            const categoriesResponse = await fetch('/api/categories');
            const categories = await categoriesResponse.json();
            
            // Map categories to tab types
            categories.forEach(category => {
                if (category.name.toLowerCase().includes('writing')) {
                    fetchServiceOptions('writing', category.id);
                } else if (category.name.toLowerCase().includes('proofreading')) {
                    fetchServiceOptions('proofreading', category.id);
                } else if (category.name.toLowerCase().includes('technical')) {
                    fetchServiceOptions('technical', category.id);
                }
            });
            
            // Fetch academic levels
            const academicLevelsResponse = await fetch('/api/academic-levels');
            const levels = await academicLevelsResponse.json();
            
            // Populate academic levels dropdown
            if (levels.length > 0) {
                mastersSelect.innerHTML = '';
                levels.forEach(level => {
                    academicLevels[level.id] = level;
                    mastersSelect.innerHTML += `<option value="${level.id}">${level.name}</option>`;
                });
                selectedAcademicLevelId = levels[0].id;
            }
            
            // Fetch deadlines
            const deadlinesResponse = await fetch('/api/deadlines');
            const deadlinesList = await deadlinesResponse.json();
            
            // Store deadlines for later use
            deadlinesList.forEach(deadline => {
                deadlines[deadline.id] = deadline;
            });
            
            // Set default deadline (7 days)
            const defaultDeadline = deadlinesList.find(d => d.hours === 168) || deadlinesList[0];
            selectedDeadlineId = defaultDeadline.id;
            
            // Initialize with the default tab's service options
            await initializeTab('writing');
            
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }
    
    // Fetch service options for a specific tab/category
    async function fetchServiceOptions(tabType, categoryId) {
        try {
            const response = await fetch(`/api/service-options/${tabType}`);
            const options = await response.json();
            
            // Store services for this tab
            services[tabType] = options;
            
            // If this is the current tab, update the dropdown
            if (tabType === currentTab) {
                updateServiceDropdown(tabType);
            }
        } catch (error) {
            console.error(`Error fetching ${tabType} options:`, error);
        }
    }
    
    // Update the service dropdown based on the current tab
    function updateServiceDropdown(tabType) {
        if (services[tabType] && services[tabType].length > 0) {
            selectInput.innerHTML = '';
            services[tabType].forEach(service => {
                selectInput.innerHTML += `<option value="${service.id}">${service.name}</option>`;
            });
            selectedServiceId = services[tabType][0].id;
            updatePrice();
        } else {
            // Default options if API fails
            selectInput.innerHTML = defaultServiceOptions[tabType].join('');
        }
    }
    
    // Initialize a tab with its service options
    async function initializeTab(tabType) {
        currentTab = tabType;
        
        // If services are already loaded for this tab, update the dropdown
        if (services[tabType]) {
            updateServiceDropdown(tabType);
        } else {
            // Otherwise use default options until API data is available
            selectInput.innerHTML = defaultServiceOptions[tabType].join('');
        }
        
        // Update counter display based on tab type
        updateCounterDisplay();
        
        // Update price
        updatePrice();
    }
    
    // Default service options for each tab (fallback if API fails)
    const defaultServiceOptions = {
        'writing': [
            '<option value="" selected>Dissertation</option>',
            '<option value="essay">Essay</option>',
            '<option value="research">Research Paper</option>',
            '<option value="thesis">Thesis</option>'
        ],
        'proofreading': [
            '<option value="" selected>Dissertation Proofreading</option>',
            '<option value="essay">Essay Proofreading</option>',
            '<option value="research">Research Paper Proofreading</option>',
            '<option value="thesis">Thesis Proofreading</option>'
        ],
        'technical': [
            '<option value="" selected>Select subject area</option>',
            '<option value="accounting">Accounting</option>',
            '<option value="business">Business</option>',
            '<option value="computer-science">Computer Science</option>',
            '<option value="economics">Economics</option>',
            '<option value="statistics">Statistics</option>',
            '<option value="mathematics">Mathematics</option>'
        ]
    };
    
    // Calculate price based on selected options
    async function calculatePrice() {
        // If API data is available, use it to calculate price
        if (selectedServiceId && selectedAcademicLevelId && selectedDeadlineId) {
            try {
                const response = await fetch('/api/calculate-price', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        service_id: selectedServiceId,
                        academic_level_id: selectedAcademicLevelId,
                        deadline_id: selectedDeadlineId,
                        page_count: pageCount
                    })
                });
                
                const data = await response.json();
                return data.total_price;
            } catch (error) {
                console.error('Error calculating price:', error);
                // Fall back to basic calculation
                return PRICES[currentTab] * pageCount;
            }
        } else {
            // Use basic calculation if API data is not available
            return PRICES[currentTab] * pageCount;
        }
    }
    
    // Update price based on current settings
    async function updatePrice() {
        const totalPrice = await calculatePrice();
        document.querySelector('.price-value').textContent = `$${totalPrice.toFixed(2)}`;
    }
    
    // Update counter display based on tab
    function updateCounterDisplay() {
        if (currentTab === 'technical') {
            counterDisplay.textContent = `${pageCount} calculation${pageCount > 1 ? 's' : ''}`;
        } else {
            counterDisplay.textContent = `${pageCount} page${pageCount > 1 ? 's' : ''} / ${pageCount * 275} words`;
        }
        updatePrice();
    }
    
    // Tab switching functionality
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all tabs
            tabButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Get the tab type
            const tabType = this.getAttribute('data-tab');
            
            // Initialize the selected tab
            initializeTab(tabType);
        });
    });
    
    // Service selection functionality
    selectInput.addEventListener('change', function() {
        selectedServiceId = this.value;
        updatePrice();
    });
    
    // Academic level selection functionality
    mastersSelect.addEventListener('change', function() {
        selectedAcademicLevelId = this.value;
        updatePrice();
    });
    
    // Page counter functionality
    decrementButton.addEventListener('click', function() {
        if (pageCount > 1) {
            pageCount--;
            updateCounterDisplay();
        }
    });
    
    incrementButton.addEventListener('click', function() {
        pageCount++;
        updateCounterDisplay();
    });
    
    // Search functionality
    function handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        
        if (event.key === 'Enter' && searchTerm) {
            window.location.href = `/search?q=${encodeURIComponent(searchTerm)}`;
        }
    }
    
    searchInput.addEventListener('keyup', handleSearch);
    mobileSearchInput.addEventListener('keyup', handleSearch);
    
    // Date picker functionality (simplified - would use a real date picker in production)
    datePicker.addEventListener('click', function() {
        // This would open a date picker in a real implementation
        alert('Date picker would open here. This would normally be implemented with a proper date picker library.');
    });
    
    // Continue button functionality
    continueButton.addEventListener('click', function() {
        // Get selected values
        const serviceId = selectedServiceId || selectInput.value;
        const academicLevelId = selectedAcademicLevelId || mastersSelect.value;
        
        // Construct URL for the order page
        const params = new URLSearchParams({
            service_id: serviceId,
            academic_level_id: academicLevelId,
            deadline_id: selectedDeadlineId,
            pages: pageCount,
            tab: currentTab
        });
        
        window.location.href = `/order?${params}`;
    });
    
    // Initialize data and UI
    fetchData();
});