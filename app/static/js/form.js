document.addEventListener('DOMContentLoaded', function() {
    const initializeFormWhenReady = async () => {
        if (window.formDataFetcher) {
            try {
                await window.formDataFetcher.init();
            } catch (error) {
                console.error('Form data initialization failed:', error);
            }
        }
        
        initializeForm();
    };

    initializeFormWhenReady();
    window.addEventListener('load', function() {
        setTimeout(() => {
            const selects = ['paperType', 'proofType', 'techType', 'academicLevel'];
            
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select && select.options.length === 1 && select.options[0].text === 'Loading...') {
                    select.innerHTML = '<option value="">Failed to load options. Please refresh the page.</option>';
                    select.classList.add('error');
                }
            });
        }, 10000);
    });
    // Tab elements
    const tabs = document.querySelectorAll('.tab');
    const paperTypeSelect = document.getElementById('paperType');
    const proofTypeSelect = document.getElementById('proofType');
    const techTypeSelect = document.getElementById('techType');
    const academicLevelSelect = document.getElementById('academicLevel');
    const dueDateInput = document.getElementById('due_date');
    const totalPriceElement = document.getElementById('totalPrice');
    const pagesTextElement = document.getElementById('pagesText');
    const decreasePagesBtn = document.getElementById('decreasePages');
    const increasePagesBtn = document.getElementById('increasePages');
    const continueBtn = document.getElementById('continueBtn');

    // Deadline mapping - matches your backend model
    const availableDeadlines = [
        { name: "3 Hours", hours: 3, order: 1 },
        { name: "6 Hours", hours: 6, order: 2 },
        { name: "12 Hours", hours: 12, order: 3 },
        { name: "24 Hours", hours: 24, order: 4 },
        { name: "48 Hours", hours: 48, order: 5 },
        { name: "3 Days", hours: 72, order: 6 },
        { name: "7 Days", hours: 168, order: 7 },
        { name: "10 Days", hours: 240, order: 8 },
        { name: "14 Days", hours: 336, order: 9 },
        { name: "20 Days", hours: 400, order: 10 }
    ];

    // State variables
    let currentTab = 'writing';
    let currentPages = 1;
    let currentWordCount = 275;
    const wordsPerPage = 275;

    // Initialize the form
    initializeForm();

    function initializeForm() {
        // Show only the writing tab initially
        showTabContent('writing');
        
        // Set minimum date to today
        const today = new Date().toISOString().slice(0, 16);
        dueDateInput.setAttribute('min', today);
        dueDateInput.value = today;
        
        // Calculate initial price
        calculatePrice();
    }

    // Tab switching functionality
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Determine which tab was clicked
            const tabText = this.textContent.toLowerCase();
            currentTab = tabText;
            
            // Show appropriate content
            showTabContent(tabText);
            
            // Recalculate price when tab changes
            calculatePrice();
        });
    });

    function showTabContent(tabType) {
        // Hide all select fields initially
        paperTypeSelect.parentElement.style.display = 'none';
        proofTypeSelect.parentElement.style.display = 'none';
        techTypeSelect.parentElement.style.display = 'none';
        
        // Show the appropriate select field based on active tab
        switch(tabType) {
            case 'writing':
                paperTypeSelect.parentElement.style.display = 'block';
                break;
            case 'proofreading':
                proofTypeSelect.parentElement.style.display = 'block';
                break;
            case 'technical':
                techTypeSelect.parentElement.style.display = 'block';
                break;
        }
    }

    // Page control functionality
    decreasePagesBtn.addEventListener('click', function() {
        if (currentPages > 1) {
            currentPages--;
            currentWordCount = currentPages * wordsPerPage;
            updatePagesDisplay();
            calculatePrice();
        }
    });

    increasePagesBtn.addEventListener('click', function() {
        currentPages++;
        currentWordCount = currentPages * wordsPerPage;
        updatePagesDisplay();
        calculatePrice();
    });

    function updatePagesDisplay() {
        pagesTextElement.textContent = `${currentPages} page${currentPages > 1 ? 's' : ''} / ${currentWordCount} words`;
    }

    // Event listeners for form changes
    paperTypeSelect.addEventListener('change', calculatePrice);
    proofTypeSelect.addEventListener('change', calculatePrice);
    techTypeSelect.addEventListener('change', calculatePrice);
    academicLevelSelect.addEventListener('change', calculatePrice);
    dueDateInput.addEventListener('change', calculatePrice);

    function getCurrentServiceId() {
        switch(currentTab) {
            case 'writing':
                return paperTypeSelect.value;
            case 'proofreading':
                return proofTypeSelect.value;
            case 'technical':
                return techTypeSelect.value;
            default:
                return null;
        }
    }

    function calculateDeadlineFromDate(dueDate) {
        if (!dueDate) return null;
        
        const now = new Date();
        const due = new Date(dueDate);
        const diffInHours = Math.ceil((due - now) / (1000 * 60 * 60));
        
        return Math.max(1, diffInHours); // Minimum 1 hour
    }

    /**
     * Maps calculated deadline hours to the best matching deadline from backend
     * @param {number} calculatedHours - Hours calculated from due date
     * @returns {object|null} - Best matching deadline object or null
     */
    function mapToClosestDeadline(calculatedHours) {
        if (!calculatedHours || calculatedHours < 1) return null;

        // If calculated hours is less than minimum deadline, use the shortest deadline
        if (calculatedHours <= availableDeadlines[0].hours) {
            return availableDeadlines[0];
        }

        // If calculated hours exceeds maximum deadline, use the longest deadline
        if (calculatedHours >= availableDeadlines[availableDeadlines.length - 1].hours) {
            return availableDeadlines[availableDeadlines.length - 1];
        }

        // Find the best matching deadline
        let bestMatch = null;
        let smallestDifference = Infinity;

        for (const deadline of availableDeadlines) {
            // Only consider deadlines that are >= calculated hours (can't deliver faster than requested)
            if (deadline.hours >= calculatedHours) {
                const difference = deadline.hours - calculatedHours;
                if (difference < smallestDifference) {
                    smallestDifference = difference;
                    bestMatch = deadline;
                }
            }
        }

        // If no deadline found that's >= calculated hours, return the closest one
        if (!bestMatch) {
            for (const deadline of availableDeadlines) {
                const difference = Math.abs(deadline.hours - calculatedHours);
                if (difference < smallestDifference) {
                    smallestDifference = difference;
                    bestMatch = deadline;
                }
            }
        }

        return bestMatch;
    }

    /**
     * Gets deadline info for display purposes
     * @param {object} deadline - Deadline object
     * @param {number} originalHours - Originally calculated hours
     * @returns {string} - Formatted deadline info
     */
    function getDeadlineDisplayInfo(deadline, originalHours) {
        if (!deadline) return '';
        
        const timeDiff = deadline.hours - originalHours;
        let info = `Selected: ${timeDiff} hours from now`;
        
        if (timeDiff > 0) {
            // info += ` (${timeDiff}h buffer)`;
        } else if (timeDiff < 0) {
            // info += ` (closest available)`;
        }
        
        return info;
    }

    async function calculatePrice() {
        const serviceId = getCurrentServiceId();
        const academicLevelId = academicLevelSelect.value;
        const dueDate = dueDateInput.value;
        
        // Check if all required fields are filled
        if (!serviceId || !academicLevelId || !dueDate) {
            totalPriceElement.textContent = '$0.00';
            updateDeadlineInfo('');
            return;
        }

        const calculatedHours = calculateDeadlineFromDate(dueDate);
        if (!calculatedHours) {
            totalPriceElement.textContent = '$0.00';
            updateDeadlineInfo('');
            return;
        }

        // Map to closest available deadline
        const matchedDeadline = mapToClosestDeadline(calculatedHours);
        if (!matchedDeadline) {
            totalPriceElement.textContent = '$0.00';
            updateDeadlineInfo('No suitable deadline found');
            return;
        }

        // Update deadline info display
        const deadlineInfo = getDeadlineDisplayInfo(matchedDeadline, calculatedHours);
        updateDeadlineInfo(deadlineInfo);

        try {
            const response = await fetch('/api/calculate-price', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value,
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    service_id: parseInt(serviceId),
                    academic_level_id: parseInt(academicLevelId),
                    deadline_id: matchedDeadline.order, // Use the deadline order/id instead of hours
                    deadline_hours: matchedDeadline.hours, // Send the matched deadline hours
                    calculated_hours: calculatedHours, // Send original calculated hours for reference
                    word_count: currentWordCount,
                    due_date: dueDate
                })
            });

            if (response.ok) {
                const data = await response.json();
                totalPriceElement.textContent = `$${data.total_price.toFixed(2)}`;
                
                // Update pages display if the backend calculated different page count
                if (data.page_count && data.page_count !== currentPages) {
                    currentPages = data.page_count;
                    currentWordCount = Math.round(currentPages * wordsPerPage);
                    updatePagesDisplay();
                }

                // Show any backend warnings about deadline adjustments
                if (data.deadline_warning) {
                    showDeadlineWarning(data.deadline_warning);
                }
            } else {
                console.error('Error calculating price:', response.statusText);
                totalPriceElement.textContent = '$0.00';
                updateDeadlineInfo('Error calculating price');
            }
        } catch (error) {
            console.error('Error calculating price:', error);
            totalPriceElement.textContent = '$0.00';
            updateDeadlineInfo('Network error');
        }
    }

    /**
     * Updates deadline information display
     * @param {string} info - Information to display
     */
    function updateDeadlineInfo(info) {
        let deadlineInfoElement = document.getElementById('deadlineInfo');
        
        // Create deadline info element if it doesn't exist
        if (!deadlineInfoElement) {
            deadlineInfoElement = document.createElement('div');
            deadlineInfoElement.id = 'deadlineInfo';
            deadlineInfoElement.className = 'deadline-info text-sm mt-1';
            deadlineInfoElement.style.fontStyle = 'italic';
            deadlineInfoElement.style.color = 'darkblue';
            
            // Insert after the due date input
            dueDateInput.parentNode.appendChild(deadlineInfoElement);
        }
        
        deadlineInfoElement.textContent = info;
        deadlineInfoElement.style.display = info ? 'block' : 'none';
    }

    /**
     * Shows deadline warning if backend suggests different deadline
     * @param {string} warning - Warning message
     */
    function showDeadlineWarning(warning) {
        let warningElement = document.getElementById('deadlineWarning');
        
        if (!warningElement) {
            warningElement = document.createElement('div');
            warningElement.id = 'deadlineWarning';
            warningElement.className = 'deadline-warning bg-yellow-100 border-l-4 border-yellow-400 p-2 mt-2 text-sm';
            
            // Insert after the deadline info
            const deadlineInfo = document.getElementById('deadlineInfo');
            if (deadlineInfo) {
                deadlineInfo.parentNode.insertBefore(warningElement, deadlineInfo.nextSibling);
            } else {
                dueDateInput.parentNode.appendChild(warningElement);
            }
        }
        
        warningElement.innerHTML = `<strong>Note:</strong> ${warning}`;
        warningElement.style.display = 'block';
        
        // Auto-hide warning after 5 seconds
        setTimeout(() => {
            warningElement.style.display = 'none';
        }, 5000);
    }

    // Continue button functionality
    continueBtn.addEventListener('click', function() {
        const serviceId = getCurrentServiceId();
        const academicLevelId = academicLevelSelect.value;
        const dueDate = dueDateInput.value;
        
        // Validate required fields
        if (!serviceId) {
            alert('Please select a service type.');
            return;
        }
        
        if (!academicLevelId) {
            alert('Please select an academic level.');
            return;
        }
        
        if (!dueDate) {
            alert('Please select a due date.');
            return;
        }
        
        // Check if due date is not in the past
        const today = new Date();
        const selectedDate = new Date(dueDate);
        if (selectedDate <= today) {
            alert('Please select a future due date.');
            return;
        }

        // Calculate final deadline mapping
        const calculatedHours = calculateDeadlineFromDate(dueDate);
        const matchedDeadline = mapToClosestDeadline(calculatedHours);
        
        if (!matchedDeadline) {
            alert('Unable to process the selected deadline. Please choose a different due date.');
            return;
        }
        
        // Collect form data
        const formData = {
            service_id: parseInt(serviceId),
            service_type: currentTab,
            academic_level_id: parseInt(academicLevelId),
            due_date: dueDate,
            calculated_hours: calculatedHours,
            deadline_id: matchedDeadline.order,
            deadline_name: matchedDeadline.name,
            deadline_hours: matchedDeadline.hours,
            pages: currentPages,
            word_count: currentWordCount,
            total_price: totalPriceElement.textContent
        };
        
        // Store form data
        sessionStorage.setItem('orderData', JSON.stringify(formData));
        
        // Log for debugging
        console.log('Order data:', formData);
        console.log('Deadline mapping:', {
            original_hours: calculatedHours,
            matched_deadline: matchedDeadline,
            time_buffer: matchedDeadline.hours - calculatedHours
        });
        
        // Trigger custom event
        const continueEvent = new CustomEvent('orderContinue', { detail: formData });
        document.dispatchEvent(continueEvent);
    });

    // Optional: Listen for custom continue event
    document.addEventListener('orderContinue', function(event) {
        console.log('Order continuation triggered:', event.detail);
        const queryString = new URLSearchParams(event.detail).toString();
        window.location.href = `orders/create?${queryString}`; 
    });

    // Utility function to get all available deadlines (for debugging or other uses)
    window.getAvailableDeadlines = function() {
        return availableDeadlines;
    };

    // Utility function to test deadline mapping (for debugging)
    window.testDeadlineMapping = function(hours) {
        return mapToClosestDeadline(hours);
    };
});