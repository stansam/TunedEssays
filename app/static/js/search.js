// interactive-search.js
// Interactive search functionality for academic and professional writing services

// Common search phrases for academic and professional writing services
const searchSuggestions = [
    { text: "Essay Writing", category: "Academic", icon: "📝" },
    { text: "Research Papers", category: "Academic", icon: "🔬" },
    { text: "Dissertation Help", category: "Academic", icon: "🎓" },
    { text: "Business Reports", category: "Professional", icon: "📊" },
    { text: "Thesis Writing", category: "Academic", icon: "📚" },
    { text: "Case Studies", category: "Professional", icon: "💼" },
    { text: "Literature Review", category: "Academic", icon: "📖" },
    { text: "Grant Proposals", category: "Professional", icon: "💰" },
    { text: "Technical Writing", category: "Professional", icon: "⚙️" },
    { text: "APA Citation", category: "Academic", icon: "✏️" },
    { text: "MLA Format", category: "Academic", icon: "📄" },
    { text: "Chicago Style", category: "Academic", icon: "📑" },
    { text: "Harvard Referencing", category: "Academic", icon: "🏛️" },
    { text: "Proofreading", category: "Both", icon: "🔍" },
    { text: "Editing Services", category: "Both", icon: "✂️" },
    { text: "Plagiarism Check", category: "Academic", icon: "🛡️" },
    { text: "Statistical Analysis", category: "Academic", icon: "📈" },
    { text: "Data Analysis", category: "Professional", icon: "📊" },
    { text: "PowerPoint Presentation", category: "Professional", icon: "📽️" },
    { text: "Lab Reports", category: "Academic", icon: "🧪" },
    { text: "Book Reviews", category: "Academic", icon: "📚" },
    { text: "Annotated Bibliography", case: "Academic", icon: "📋" },
    { text: "Personal Statement", category: "Academic", icon: "👤" },
    { text: "Cover Letter", category: "Professional", icon: "💌" },
    { text: "Resume Writing", category: "Professional", icon: "📄" }
];

class InteractiveSearch {
    constructor() {
        this.dropdown = document.getElementById('searchDropdown');
        this.searchInputs = document.querySelectorAll('.search-input, .mobile-search-input');
        this.currentQuery = '';
        this.debounceTimer = null;
        this.selectedIndex = -1;
        
        this.init();
    }

    init() {
        // Create dropdown if it doesn't exist
        if (!this.dropdown) {
            this.createDropdown();
        }

        this.searchInputs.forEach(input => {
            input.addEventListener('input', (e) => this.handleInput(e));
            input.addEventListener('focus', (e) => this.handleFocus(e));
            input.addEventListener('keydown', (e) => this.handleKeydown(e));
            input.addEventListener('blur', (e) => this.handleBlur(e));
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.hideDropdown();
            }
        });

        // Handle form submissions with validation
        document.querySelectorAll('.search-bar, .mobile-search-bar').forEach(form => {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        });
    }

    createDropdown() {
        const container = document.querySelector('.search-container') || 
                         document.querySelector('.search-bar').parentElement;
        
        if (container) {
            const dropdown = document.createElement('div');
            dropdown.id = 'searchDropdown';
            dropdown.className = 'search-dropdown';
            container.appendChild(dropdown);
            this.dropdown = dropdown;
        }
    }

    handleInput(e) {
        const query = e.target.value.trim();
        this.currentQuery = query;
        this.selectedIndex = -1;

        // Sync both inputs
        this.syncInputs(query);

        // Clear previous debounce timer
        clearTimeout(this.debounceTimer);

        // Debounce the search to avoid too many rapid updates
        this.debounceTimer = setTimeout(() => {
            if (query.length > 0) {
                this.showSuggestions(query);
            } else {
                this.hideDropdown();
            }
        }, 150);
    }

    handleFocus(e) {
        const query = e.target.value.trim();
        if (query.length > 0) {
            this.showSuggestions(query);
        } else {
            this.showDefaultSuggestions();
        }
    }

    handleBlur(e) {
        // Delay hiding to allow for clicks on dropdown items
        setTimeout(() => {
            if (!document.querySelector('.search-dropdown:hover')) {
                this.hideDropdown();
            }
        }, 150);
    }

    handleKeydown(e) {
        const items = this.dropdown.querySelectorAll('.dropdown-item[data-value]');
        
        switch(e.key) {
            case 'Escape':
                this.hideDropdown();
                e.target.blur();
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.navigateItems(items, 'down');
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateItems(items, 'up');
                break;
            case 'Enter':
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    e.preventDefault();
                    this.selectSuggestion(items[this.selectedIndex].dataset.value);
                }
                break;
            case 'Tab':
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    e.preventDefault();
                    this.selectSuggestion(items[this.selectedIndex].dataset.value);
                }
                break;
        }
    }

    handleSubmit(e) {
        const formData = new FormData(e.target);
        const query = formData.get('q');
        
        if (!query || query.trim() === '') {
            e.preventDefault();
            this.showError('Please enter a search term');
            return false;
        }

        // Hide dropdown and allow form to submit
        this.hideDropdown();
        return true;
    }

    syncInputs(value) {
        this.searchInputs.forEach(input => {
            if (input !== document.activeElement) {
                input.value = value;
            }
        });
    }

    showSuggestions(query) {
        const filtered = searchSuggestions.filter(item => 
            item.text.toLowerCase().includes(query.toLowerCase()) ||
            item.category.toLowerCase().includes(query.toLowerCase())
        );

        if (filtered.length === 0) {
            this.showNoResults(query);
            return;
        }

        // Prioritize exact matches and starts-with matches
        filtered.sort((a, b) => {
            const aLower = a.text.toLowerCase();
            const bLower = b.text.toLowerCase();
            const queryLower = query.toLowerCase();
            
            if (aLower.startsWith(queryLower) && !bLower.startsWith(queryLower)) return -1;
            if (!aLower.startsWith(queryLower) && bLower.startsWith(queryLower)) return 1;
            return aLower.localeCompare(bLower);
        });

        const html = filtered.slice(0, 10).map((item, index) => `
            <div class="dropdown-item" data-value="${item.text}" data-index="${index}">
                <span class="dropdown-icon">${item.icon}</span>
                <span class="dropdown-text">${this.highlightMatch(item.text, query)}</span>
                <span class="dropdown-category">${item.category}</span>
            </div>
        `).join('');

        this.dropdown.innerHTML = html;
        this.showDropdown();
        this.bindItemEvents();
        this.selectedIndex = -1;
    }

    showDefaultSuggestions() {
        const popular = searchSuggestions.slice(0, 8);
        const html = `
            <div class="dropdown-header">Popular Searches</div>
            ${popular.map((item, index) => `
                <div class="dropdown-item" data-value="${item.text}" data-index="${index}">
                    <span class="dropdown-icon">${item.icon}</span>
                    <span class="dropdown-text">${item.text}</span>
                    <span class="dropdown-category">${item.category}</span>
                </div>
            `).join('')}
        `;

        this.dropdown.innerHTML = html;
        this.showDropdown();
        this.bindItemEvents();
        this.selectedIndex = -1;
    }

    showNoResults(query) {
        this.dropdown.innerHTML = `
            <div class="dropdown-item no-results">
                <span class="dropdown-icon">🔍</span>
                <span class="dropdown-text">No suggestions found for "${query}"</span>
                <span class="dropdown-help">Press Enter to search anyway</span>
            </div>
        `;
        this.showDropdown();
    }

    showError(message) {
        this.dropdown.innerHTML = `
            <div class="dropdown-item error">
                <span class="dropdown-icon">⚠️</span>
                <span class="dropdown-text">${message}</span>
            </div>
        `;
        this.showDropdown();
        setTimeout(() => this.hideDropdown(), 2000);
    }

    highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }

    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    bindItemEvents() {
        const items = this.dropdown.querySelectorAll('.dropdown-item[data-value]');
        items.forEach((item, index) => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.selectSuggestion(item.dataset.value);
            });

            item.addEventListener('mouseenter', () => {
                this.setSelectedIndex(index);
            });
        });
    }

    selectSuggestion(value) {
        this.searchInputs.forEach(input => {
            input.value = value;
        });
        this.hideDropdown();
        
        // Submit the form
        const activeInput = document.querySelector('.search-input:focus, .mobile-search-input:focus') ||
                           document.querySelector('.search-input');
        if (activeInput) {
            activeInput.closest('form').submit();
        }
    }

    navigateItems(items, direction) {
        if (items.length === 0) return;
        
        // Clear current selection
        items.forEach(item => item.classList.remove('selected'));
        
        if (direction === 'down') {
            this.selectedIndex = this.selectedIndex < items.length - 1 ? this.selectedIndex + 1 : 0;
        } else {
            this.selectedIndex = this.selectedIndex > 0 ? this.selectedIndex - 1 : items.length - 1;
        }
        
        this.setSelectedIndex(this.selectedIndex);
    }

    setSelectedIndex(index) {
        const items = this.dropdown.querySelectorAll('.dropdown-item[data-value]');
        
        // Clear all selections
        items.forEach(item => item.classList.remove('selected'));
        
        // Set new selection
        if (index >= 0 && index < items.length) {
            this.selectedIndex = index;
            items[index].classList.add('selected');
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    showDropdown() {
        if (this.dropdown) {
            // Position the dropdown relative to the active search input
            const activeInput = document.querySelector('.search-input:focus, .mobile-search-input:focus') ||
                               document.querySelector('.search-input, .mobile-search-input');
            
            if (activeInput) {
                const searchContainer = activeInput.closest('.search-container');
                const searchBar = activeInput.closest('.search-bar, .mobile-search-bar');
                
                if (searchContainer && searchBar) {
                    // Get the position of the search bar
                    const rect = searchBar.getBoundingClientRect();
                    const containerRect = searchContainer.getBoundingClientRect();
                    
                    // Position dropdown relative to container
                    this.dropdown.style.top = `${searchBar.offsetTop + searchBar.offsetHeight + 8}px`;
                    this.dropdown.style.left = `${searchBar.offsetLeft}px`;
                    this.dropdown.style.width = `${searchBar.offsetWidth}px`;
                }
            }
            
            this.dropdown.classList.add('show');
            document.querySelector('.hero-header').style.display = 'none';
        }
    }

    hideDropdown() {
        if (this.dropdown) {
            this.dropdown.classList.remove('show');
            document.querySelector('.hero-header').style.display = 'block';
        }
        this.selectedIndex = -1;
    }
}

// Initialize the interactive search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if search elements exist before initializing
    const searchElements = document.querySelectorAll('.search-input, .mobile-search-input');
    if (searchElements.length > 0) {
        new InteractiveSearch();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InteractiveSearch;
}