/**
 * Form Data Fetcher - Handles dynamic loading of form select options
 * This script fetches form data from API endpoints and populates select fields
 */

class FormDataFetcher {
    constructor() {
        this.cache = new Map();
        this.isInitialized = false;
        
        // API endpoints configuration
        this.endpoints = {
            services: '/api/get-services',
            academicLevels: '/api/academic-levels',
            deadlines: '/api/deadlines'
        };
        
        // Select field mappings
        this.selectFields = {
            paperType: document.getElementById('paperType'),
            proofType: document.getElementById('proofType'),
            techType: document.getElementById('techType'),
            academicLevel: document.getElementById('academicLevel')
        };
        
        // Loading states
        this.loadingStates = new Set();
    }

    /**
     * Initialize the form data fetcher
     */
    async init() {
        if (this.isInitialized) return;
        
        try {
            // Show loading states
            this.showLoadingStates();
            
            // Fetch all required data
            await Promise.all([
                this.fetchServices(),
                this.fetchAcademicLevels()
            ]);
            
            // Populate form fields
            this.populateFormFields();
            
            this.isInitialized = true;
            console.log('FormDataFetcher initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize FormDataFetcher:', error);
            this.showErrorStates();
        } finally {
            this.hideLoadingStates();
        }
    }

    /**
     * Fetch services data from API
     */
    async fetchServices() {
        if (this.cache.has('services')) {
            return this.cache.get('services');
        }

        try {
            const response = await fetch(this.endpoints.services, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Organize services by category
            const organizedServices = {
                writing: data.filter(service => service.pricing_category_id === 1),
                proofreading: data.filter(service => service.pricing_category_id === 2),
                technical: data.filter(service => service.pricing_category_id === 3),
                humanizing_ai: data.filter(service => service.pricing_category_id === 4)
            };

            this.cache.set('services', organizedServices);
            return organizedServices;

        } catch (error) {
            console.error('Error fetching services:', error);
            throw error;
        }
    }

    /**
     * Fetch academic levels data from API
     */
    async fetchAcademicLevels() {
        if (this.cache.has('academicLevels')) {
            return this.cache.get('academicLevels');
        }

        try {
            const response = await fetch(this.endpoints.academicLevels, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.cache.set('academicLevels', data);
            return data;

        } catch (error) {
            console.error('Error fetching academic levels:', error);
            throw error;
        }
    }

    /**
     * Populate all form select fields with fetched data
     */
    populateFormFields() {
        const services = this.cache.get('services');
        const academicLevels = this.cache.get('academicLevels');

        if (services) {
            this.populateServiceSelects(services);
        }

        if (academicLevels) {
            this.populateAcademicLevelSelect(academicLevels);
        }
    }

    /**
     * Populate service select fields
     */
    populateServiceSelects(services) {
        // Populate writing services
        if (this.selectFields.paperType) {
            this.populateSelect(
                this.selectFields.paperType, 
                services.writing, 
                'Choose a service'
            );
        }

        // Populate proofreading services (including humanizing AI)
        if (this.selectFields.proofType) {
            const proofreadingServices = [
                ...services.proofreading,
                ...services.humanizing_ai
            ];
            this.populateSelect(
                this.selectFields.proofType, 
                proofreadingServices, 
                'Choose a service'
            );
        }

        // Populate technical services
        if (this.selectFields.techType) {
            this.populateSelect(
                this.selectFields.techType, 
                services.technical, 
                'Choose a service'
            );
        }
    }

    /**
     * Populate academic level select field
     */
    populateAcademicLevelSelect(academicLevels) {
        if (this.selectFields.academicLevel) {
            this.populateSelect(
                this.selectFields.academicLevel, 
                academicLevels, 
                'Level'
            );
        }
    }

    /**
     * Generic method to populate a select field
     */
    populateSelect(selectElement, options, placeholderText) {
        if (!selectElement || !Array.isArray(options)) return;

        // Clear existing options
        selectElement.innerHTML = '';

        // Add placeholder option
        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = placeholderText;
        selectElement.appendChild(placeholderOption);

        // Add options from data
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.id;
            optionElement.textContent = option.name;
            selectElement.appendChild(optionElement);
        });

        // Remove loading class
        selectElement.classList.remove('loading');
    }

    /**
     * Trigger updates for custom dropdowns after data is loaded
     */
    triggerCustomDropdownUpdates() {
        // Wait a bit for DOM to update, then trigger custom dropdown refresh
        setTimeout(() => {
            // Dispatch custom event to notify custom dropdowns to update
            const event = new CustomEvent('selectOptionsUpdated');
            document.dispatchEvent(event);
            
            // Also manually trigger the MutationObserver for each select
            Object.values(this.selectFields).forEach(select => {
                if (select) {
                    // Trigger a DOM change to activate MutationObserver
                    const event = new Event('change');
                    select.dispatchEvent(event);
                }
            });
        }, 100);
    }

    /**
     * Show loading states for select fields
     */
    showLoadingStates() {
        Object.values(this.selectFields).forEach(select => {
            if (select) {
                select.classList.add('loading');
                select.innerHTML = '<option value="">Loading...</option>';
                select.disabled = true;
                this.loadingStates.add(select);
            }
        });
    }

    /**
     * Hide loading states for select fields
     */
    hideLoadingStates() {
        this.loadingStates.forEach(select => {
            select.classList.remove('loading');
            select.disabled = false;
        });
        this.loadingStates.clear();
    }

    /**
     * Show error states for select fields
     */
    showErrorStates() {
        Object.values(this.selectFields).forEach(select => {
            if (select && select.classList.contains('loading')) {
                select.classList.remove('loading');
                select.classList.add('error');
                select.innerHTML = '<option value="">Error loading options</option>';
                select.disabled = false;
            }
        });
    }

    /**
     * Refresh form data (clears cache and refetches)
     */
    async refresh() {
        this.cache.clear();
        this.isInitialized = false;
        await this.init();
    }

    /**
     * Get cached data
     */
    getCachedData(key) {
        return this.cache.get(key);
    }

    /**
     * Check if data is cached
     */
    isCached(key) {
        return this.cache.has(key);
    }

    /**
     * Get current loading state
     */
    isLoading() {
        return this.loadingStates.size > 0;
    }
}

// Create global instance
window.formDataFetcher = new FormDataFetcher();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form data fetcher
    window.formDataFetcher.init().catch(error => {
        console.error('Failed to initialize form data:', error);
    });
});

// Export for module systems (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormDataFetcher;
}