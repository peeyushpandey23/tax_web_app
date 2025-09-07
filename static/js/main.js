// Tax Advisor Application - Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // Get the Start button element
    const startButton = document.getElementById('startButton');
    
    // Add click event listener to the Start button
    if (startButton) {
        startButton.addEventListener('click', handleStartClick);
        
        // Add keyboard support for accessibility
        startButton.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleStartClick();
            }
        });
    }
    
    // Handle Start button click
    function handleStartClick() {
        console.log('Start button clicked - Navigating to upload page');
        
        // Add visual feedback
        startButton.style.transform = 'scale(0.95)';
        startButton.textContent = 'Starting...';
        startButton.disabled = true;
        
        // Navigate to upload page
        setTimeout(() => {
            window.location.href = '/upload';
        }, 500);
    }
    

    
    // Add smooth scroll behavior for better UX
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Add loading animation for better perceived performance
    window.addEventListener('load', function() {
        document.body.classList.add('loaded');
    });
    
    // Add intersection observer for scroll animations (future enhancement)
    if ('IntersectionObserver' in window) {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);
        
        // Observe elements for scroll animations
        const animatedElements = document.querySelectorAll('.hero-title, .hero-subtitle, .hero-description, .cta-button, .trust-indicators');
        animatedElements.forEach(el => observer.observe(el));
    }
    
    // Add error handling for font loading
    document.fonts.ready.then(function() {
        // Check if Aptos font is loaded
        if (document.fonts.check('1em Aptos')) {
            console.log('Aptos font loaded successfully');
        } else {
            console.warn('Aptos font not loaded, falling back to system fonts');
        }
    }).catch(function(error) {
        console.warn('Font loading error:', error);
    });
    
    // Add performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const perfData = performance.getEntriesByType('navigation')[0];
                if (perfData) {
                    console.log('Page load time:', Math.round(perfData.loadEventEnd - perfData.loadEventStart), 'ms');
                }
            }, 0);
        });
    }
});

// Add CSS animations for the hero container
const style = document.createElement('style');
style.textContent = `
    .loaded .hero-container {
        opacity: 1;
    }
    
    .hero-container {
        opacity: 0;
        transition: opacity 0.5s ease-out;
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease-out forwards;
    }
    
    @keyframes fadeInUp {
        from { 
            opacity: 0; 
            transform: translateY(30px); 
        }
        to { 
            opacity: 1; 
            transform: translateY(0); 
        }
    }
`;
document.head.appendChild(style);

