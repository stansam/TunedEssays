document.addEventListener('DOMContentLoaded', function() {
            // Fetch blog posts from the Flask backend API
            async function fetchBlogPosts() {
                try {
                    const response = await fetch('/api/blog/featured');
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    
                    const blogPosts = await response.json();
                    return blogPosts;
                } catch (error) {
                    console.error('Error fetching blog posts:', error);
                    // Return empty array in case of error
                    return [];
                }
            }

            // Function to create blog cards
            async function initBlogCarousel() {
                const blogPosts = await fetchBlogPosts();
                const carouselContainer = document.getElementById('blogCarousel');
                
                // Clear any existing content
                carouselContainer.innerHTML = '';
                
                if (blogPosts.length === 0) {
                    const noPostsMessage = document.createElement('div');
                    noPostsMessage.className = 'no-posts-message';
                    noPostsMessage.textContent = 'No blog posts found.';
                    carouselContainer.appendChild(noPostsMessage);
                    return;
                }
                
                blogPosts.forEach(post => {
                    const card = document.createElement('div');
                    card.className = 'blog-card';
                    
                    // Handle missing data gracefully
                    const title = post.title || 'Untitled Post';
                    const slug = post.slug || `post-${post.id}`;
                    const excerpt = post.excerpt || 'No excerpt available.';
                    const featuredImage = post.featured_image ? `/static/${post.featured_image}` : '/static/uploads/placeholder.webp';
                    const categoryName = post.category?.name || 'Uncategorized';
                    const publishedDate = post.published_at || post.created_at || new Date().toISOString();
                    const tags = post.tags.split(',').map(tag => tag.trim());
                    
                    // Get author details
                    let authorName = 'Anonymous';
                    let authorInitials = 'AU';
                    
                    if (post.author) {
                        authorName = post.author.name || 'Anonymous';
                        
                        if (post.author.initials) {
                            authorInitials = post.author.initials;
                        } else {
                            const nameParts = authorName.split(' ');
                            if (nameParts.length >= 2) {
                                authorInitials = nameParts[0].charAt(0) + nameParts[1].charAt(0);
                            } else if (nameParts.length === 1) {
                                authorInitials = nameParts[0].charAt(0);
                            }
                        }
                    }
                    const tagButtons = tags.map(tag => 
                        `<a href="/search?q=${encodeURIComponent(tag)}" class="btn rounded-pill btn-outline-success">${tag}</a>`
                    ).join('');
                    card.innerHTML = `
                        <div class="blog-image">
                            <img src="${featuredImage}" alt="${title}">
                        </div>
                        <div class="blog-content">
                            <span class="blog-category">${categoryName}</span>
                            <h3 class="blog-title">${title}</h3>
                            <p class="blog-excerpt">${excerpt}</p>
                            <div class="blog-footer">
                                <div class="blog-author">
                                    <div class="author-avatar">${authorInitials}</div>
                                    <div class="author-info">
                                        <span class="author-name">${authorName}</span>
                                        <span class="post-date">${formatDate(publishedDate)}</span>
                                    </div>
                                </div>
                                <a href="/blog/${slug}" class="read-more">
                                    Read More
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M5 12h14"></path>
                                        <path d="M12 5l7 7-7 7"></path>
                                    </svg>
                                </a>
                                
                            </div>
                            <div class="blog-tags" style="margin-top: 3rem; display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end;">
                                ${tagButtons}
                            </div>
                        </div>
                    `;
                    
                    carouselContainer.appendChild(card);
                });
                
                // After cards are created, set up carousel navigation
                setupCarouselNavigation();
            }
            

            // Format date function
            function formatDate(dateString) {
                const options = { year: 'numeric', month: 'long', day: 'numeric' };
                return new Date(dateString).toLocaleDateString(undefined, options);
            }
            
            // Setup carousel navigation
            function setupCarouselNavigation() {
                const carousel = document.getElementById('blogCarousel');
                const cards = carousel.querySelectorAll('.blog-card');
                
                if (cards.length === 0) return;
                
                const cardWidth = cards[0].offsetWidth;
                const gap = 24; // 1.5rem gap
                
                let currentIndex = 0;
                const maxIndex = Math.max(0, cards.length - getVisibleCards());
                
                function updateCarousel() {
                    const carousel = document.getElementById('blogCarousel');
                    const cards = carousel.querySelectorAll('.blog-card');
                    
                    if (cards.length === 0) return;
                    
                    const cardWidth = cards[0].offsetWidth;
                    const gap = 24; // 1.5rem gap
                    const slideAmount = currentIndex * (cardWidth + gap);
                    carousel.style.transform = `translateX(-${slideAmount}px)`;
                }
                updateNavigationButtons();
    
                document.getElementById('nextBtn').addEventListener('click', function() {
                    if (currentIndex < maxIndex) {
                        currentIndex++;
                        updateCarousel();
                        updateNavigationButtons();
                    }
                });
    
                document.getElementById('prevBtn').addEventListener('click', function() {
                    if (currentIndex > 0) {
                        currentIndex--;
                        updateCarousel();
                        updateNavigationButtons();
                    }
                });
                
                function updateNavigationButtons() {
                    document.getElementById('prevBtn').disabled = currentIndex === 0;
                    document.getElementById('nextBtn').disabled = currentIndex >= maxIndex;
                    
                    // Update button styles based on disabled state
                    if (currentIndex === 0) {
                        document.getElementById('prevBtn').classList.add('disabled');
                    } else {
                        document.getElementById('prevBtn').classList.remove('disabled');
                    }
                    
                    if (currentIndex >= maxIndex) {
                        document.getElementById('nextBtn').classList.add('disabled');
                    } else {
                        document.getElementById('nextBtn').classList.remove('disabled');
                    }
                }
                
                // Update carousel on window resize
                window.addEventListener('resize', function() {
                    // Recalculate card width and visible cards
                    const newCardWidth = cards[0].offsetWidth;
                    const newMaxIndex = Math.max(0, cards.length - getVisibleCards());
                    
                    
                    if (currentIndex > newMaxIndex) {
                        currentIndex = newMaxIndex;
                    }
                    
                    // Update carousel position
                    updateCarousel();
                    updateNavigationButtons();
                });
            }
    
            function getVisibleCards() {
                const viewportWidth = window.innerWidth;
                if (viewportWidth >= 992) {
                    return 3; // Show 3 cards on large screens
                } else if (viewportWidth >= 768) {
                    return 2; // Show 2 cards on medium screens
                } else {
                    return 1; // Show 1 card on small screens
                }
            }
    
            
            // Initialize the carousel
            initBlogCarousel();
        });