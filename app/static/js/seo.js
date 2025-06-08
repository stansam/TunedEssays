function toggleContent(button) {
    const column = button.closest('.seo-column');
    const content = column.querySelector('.collapsible-content');
    const icon = button.querySelector('.expand-icon');
    const text = button.querySelector('span');
    
    column.classList.toggle('expanded');
    
    if (column.classList.contains('expanded')) {
        text.textContent = 'Show Less';
    } else {
        text.textContent = 'View More Services';
    }
}

// Smooth scroll behavior for the container
document.querySelector('.seo-container').style.scrollBehavior = 'smooth';

// Add intersection observer for fade-in animation
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
        }
    });
}, { threshold: 0.1 });

observer.observe(document.querySelector('.seo-section'));