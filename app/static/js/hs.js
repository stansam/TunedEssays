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
    const dueDateInput = document.getElementById('deadline');
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
        initializeFlatpickr();
        // Set minimum date to today
        // const today = new Date().toISOString().slice(0, 16);
        // dueDateInput.setAttribute('min', today);
        // dueDateInput.value = today;
        
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
    function initializeFlatpickr() {
        const deadlinePicker = document.getElementById('deadline_picker');
        // const today =  
        
        flatpickrInstance = flatpickr(deadlinePicker, {
            enableTime: true,
            dateFormat: "Y-m-d, H:i",
            plugins: [new confirmDatePlugin({})],
            altFormat: "h:i K, M d",
            altInput: true,
            time_24hr: true,
            minDate: new Date(Date.now() + 3 * 60 * 60 * 1000), // 3 hours from now
            maxDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year from now
            minuteIncrement: 30,
            defaultDate: new Date(Date.now() + 3 * 60 * 60 * 1000),
            defaultHour: 23,
            defaultMinute: 59,
            confirmIcon: "<i class='fa fa-check'></i>", // your icon's html, if you wish to override
            confirmText: "OK ",
            showAlways: false,
            disableMobile: true,
            theme: "dark",
            onChange: function(selectedDates, dateStr, instance) {
                if (selectedDates.length > 0) {
                    const selectedDate = selectedDates[0];
                    const now = new Date();
                    const timeDiff = selectedDate - now;
                    const hoursUntilDeadline = timeDiff / (1000 * 60 * 60);
                    
                    
                    // Update deadline info
                    const dText = getDeadlineDisplayInfo(hoursUntilDeadline)
                    updateDeadlineInfo(dText);

                    
                    // Store the formatted date in hidden field

                    document.getElementById('deadline').value = hoursUntilDeadline;
                    document.getElementById('dateDue').value = dateStr;
                    // Recalculate price
                    calculatePrice();
                }
            },
            onReady: function(selectedDates, dateStr, instance) {
                // Add custom time buttons
                addCustomTimeButtons(instance);
            }
        });
    }

    function addCustomTimeButtons(instance) {
        if (!instance || !instance.calendarContainer) {
            console.warn('Flatpickr instance or calendarContainer not available');
            return;
        }
        const calendarContainer = instance.calendarContainer;
        if (calendarContainer.querySelector('.flatpickr-time-buttons')) {
            return;
        }
        // Create time buttons container
        const timeButtonsContainer = document.createElement('div');
        timeButtonsContainer.className = 'flatpickr-time-buttons';
        timeButtonsContainer.style.cssText = `
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 10px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        `;

        // Time options
        const timeOptions = [
            { label: '3 hours', hours: 3 },
            { label: '6 hours', hours: 6 },
            { label: '12 hours', hours: 12 },
            { label: '24 hours', hours: 24 },
            { label: '2 days', hours: 48 },
            { label: '3 days', hours: 72 },
            { label: '7 days', hours: 168 },
            { label: '14 days', hours: 336 }
        ];

        timeOptions.forEach(option => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = option.label;
            btn.className = 'flatpickr-time-btn';
            btn.style.cssText = `
                padding: 4px 8px;
                border: 1px solid #ddd;
                background: white;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            `;
            
            btn.addEventListener('click', function() {
                const futureDate = new Date(Date.now() + option.hours * 60 * 60 * 1000);
                instance.setDate(futureDate, true);
                // calculatePrice();
                 const now = new Date();
                 const timeDiff = futureDate - now;
                 const hoursUntilDeadline = timeDiff / (1000 * 60 * 60);

                 const deadlineTtt = getDeadlineDisplayInfo(hoursUntilDeadline);
                 updateDeadlineInfo(deadlineTtt)

                 const formattedDate = instance.formatDate(futureDate, "Y-m-d, H:i");
                 document.getElementById('deadline').value = hoursUntilDeadline;
                 document.getElementById('dateDue').value = formattedDate
            });
            
            timeButtonsContainer.appendChild(btn);
        });

        calendarContainer.appendChild(timeButtonsContainer);
    }
    // function calculateDeadlineFromDate(dueDate) {
    //     if (!dueDate) return null;
        
    //     const now = new Date();
    //     const due = new Date(dueDate);
    //     const diffInHours = Math.ceil((due - now) / (1000 * 60 * 60));
        
    //     return Math.max(1, diffInHours); // Minimum 1 hour
    // }

    // /**
    //  * Maps calculated deadline hours to the best matching deadline from backend
    //  * @param {number} calculatedHours - Hours calculated from due date
    //  * @returns {object|null} - Best matching deadline object or null
    //  */
    // function mapToClosestDeadline(calculatedHours) {
    //     if (!calculatedHours || calculatedHours < 1) return null;

    //     // If calculated hours is less than minimum deadline, use the shortest deadline
    //     if (calculatedHours <= availableDeadlines[0].hours) {
    //         return availableDeadlines[0];
    //     }

    //     // If calculated hours exceeds maximum deadline, use the longest deadline
    //     if (calculatedHours >= availableDeadlines[availableDeadlines.length - 1].hours) {
    //         return availableDeadlines[availableDeadlines.length - 1];
    //     }

    //     // Find the best matching deadline
    //     let bestMatch = null;
    //     let smallestDifference = Infinity;

    //     for (const deadline of availableDeadlines) {
    //         // Only consider deadlines that are >= calculated hours (can't deliver faster than requested)
    //         if (deadline.hours >= calculatedHours) {
    //             const difference = deadline.hours - calculatedHours;
    //             if (difference < smallestDifference) {
    //                 smallestDifference = difference;
    //                 bestMatch = deadline;
    //             }
    //         }
    //     }

    //     // If no deadline found that's >= calculated hours, return the closest one
    //     if (!bestMatch) {
    //         for (const deadline of availableDeadlines) {
    //             const difference = Math.abs(deadline.hours - calculatedHours);
    //             if (difference < smallestDifference) {
    //                 smallestDifference = difference;
    //                 bestMatch = deadline;
    //             }
    //         }
    //     }

    //     return bestMatch;
    // }

    
    function getDeadlineDisplayInfo(hours_until_deadline) {
        const days = Math.floor(hours_until_deadline / 24);
        const hours = Math.round(hours_until_deadline % 24);
        const mins = Math.round((hours_until_deadline % 1)* 60);
        let info = '';
        if (days > 0) {
            info = `${days} Day${days > 1 ? 's' : ''}`;
            if (hours > 0) info += ` : ${hours} hour${hours > 1 ? 's' : ''} from now.`;
            // if (mins > 0) info += ` : ${mins} min${mins > 1 ? 's' : ''}`;
        } else if (hours > 0) {
            info = `${hours} hour${hours > 1 ? 's' : ''} from now.`;
            // if (mins > 0) info += ` : ${mins} min${mins > 1 ? 's' : ''}`;
        } else {
            // info = `${mins} min${mins > 1 ? 's' : ''}`;
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

        const calculatedHours = document.getElementById('deadline');
        if (!calculatedHours) {
            totalPriceElement.textContent = '$0.00';
            updateDeadlineInfo('');
            return;
        }


        const deadlineInfo = getDeadlineDisplayInfo(dueDate);
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
                    deadline_data: dueDate, 
                    word_count: currentWordCount,
                })
            });

            if (response.ok) {
                const data = await response.json();
                totalPriceElement.textContent = `$${data.total_price.toFixed(2)}`;
                
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

    function updateDeadlineInfo(info) {
        let deadlineInfoElement = document.getElementById('deadlineInfo');
        
        if (!deadlineInfoElement) {
            deadlineInfoElement = document.createElement('div');
            deadlineInfoElement.id = 'deadlineInfo';
            deadlineInfoElement.className = 'deadline-info text-sm mt-1';
            deadlineInfoElement.style.fontStyle = 'italic';
            deadlineInfoElement.style.color = 'darkblue';
            
            dueDateInput.parentNode.appendChild(deadlineInfoElement);
        }
        
        deadlineInfoElement.textContent = info;
        deadlineInfoElement.style.display = info ? 'block' : 'none';
    }

    function showDeadlineWarning(warning) {
        let warningElement = document.getElementById('deadlineText');
        
        if (!warningElement) {
            warningElement = document.createElement('div');
            warningElement.id = 'deadlineWarning';
            warningElement.className = 'deadline-warning bg-yellow-100 border-l-4 border-yellow-400 p-2 mt-2 text-sm';
            
            const deadlineInfo = document.getElementById('deadlineInfo');
            if (deadlineInfo) {
                deadlineInfo.parentNode.insertBefore(warningElement, deadlineInfo.nextSibling);
            } else {
                dueDateInput.parentNode.appendChild(warningElement);
            }
        }
        
        warningElement.innerHTML = `<strong>Note:</strong> ${warning}`;
        warningElement.style.display = 'block';
        
        setTimeout(() => {
            warningElement.style.display = 'none';
        }, 5000);
    }

    continueBtn.addEventListener('click', function() {
        const serviceId = getCurrentServiceId();
        const academicLevelId = academicLevelSelect.value;
        const dueDate = dueDateInput.value;
        const actualDate = document.getElementById('dateDue').value;
        
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
        
        
        if (dueDate <= 0) {
            alert('Please select a future due date.');
            return;
        }       
        const formData = {
            service_id: parseInt(serviceId),
            academic_level_id: parseInt(academicLevelId),
            due_date: actualDate,
            deadline: dueDate,
            word_count: currentWordCount,
        };
        
        sessionStorage.setItem('orderData', JSON.stringify(formData));
        
        console.log('Order data:', formData);
        
        const continueEvent = new CustomEvent('orderContinue', { detail: formData });
        document.dispatchEvent(continueEvent);
    });

    document.addEventListener('orderContinue', function(event) {
        console.log('Order continuation triggered:', event.detail);
        const queryString = new URLSearchParams(event.detail).toString();
        window.location.href = `orders/create?${queryString}`; 
    });



});