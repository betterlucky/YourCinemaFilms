// Search functionality for YourCinemaFilms
document.addEventListener('DOMContentLoaded', function() {
    console.log('Search.js loaded and ready');
    
    // Handle click on search results to navigate to film detail page
    document.addEventListener('click', function(e) {
        const searchResultLink = e.target.closest('.search-result-link');
        if (searchResultLink) {
            console.log('Search result link clicked:', searchResultLink);
            console.log('Link href:', searchResultLink.getAttribute('href'));
            console.log('Link data-film-id:', searchResultLink.getAttribute('data-film-id'));
            
            e.preventDefault();
            
            // Try to get the href attribute first (preferred method)
            const detailUrl = searchResultLink.getAttribute('href');
            if (detailUrl) {
                console.log('Navigating to:', detailUrl);
                window.location.href = detailUrl;
                return;
            }
            
            // Fallback: Try to get the film ID from data attribute
            const filmId = searchResultLink.getAttribute('data-film-id');
            if (filmId) {
                console.log('Film ID found:', filmId);
                // Construct the URL using the film ID and the correct URL pattern
                let detailPageUrl = '/film/' + filmId + '/';
                
                // Check if we're in classics page and add source parameter
                if (window.location.pathname.includes('classics')) {
                    detailPageUrl += '?source=classics';
                }
                
                console.log('Navigating to constructed URL:', detailPageUrl);
                window.location.href = detailPageUrl;
            }
        }
    });
    
    // For jQuery-based search in the navbar
    if (typeof jQuery !== 'undefined') {
        console.log('jQuery detected, setting up jQuery handlers');
        
        jQuery(document).on('click', '.search-result-link', function(e) {
            console.log('jQuery: Search result link clicked:', this);
            console.log('jQuery: Link href:', jQuery(this).attr('href'));
            console.log('jQuery: Link data-film-id:', jQuery(this).attr('data-film-id'));
            
            e.preventDefault();
            
            // Try to get the href attribute first
            const detailUrl = jQuery(this).attr('href');
            if (detailUrl) {
                console.log('jQuery: Navigating to:', detailUrl);
                window.location.href = detailUrl;
                return;
            }
            
            // Fallback: Try to get the film ID
            const filmId = jQuery(this).attr('data-film-id');
            if (filmId) {
                console.log('jQuery: Film ID found:', filmId);
                // Construct the URL using the film ID and the correct URL pattern
                let detailPageUrl = '/film/' + filmId + '/';
                
                // Check if we're in classics page and add source parameter
                if (window.location.pathname.includes('classics')) {
                    detailPageUrl += '?source=classics';
                }
                
                console.log('jQuery: Navigating to constructed URL:', detailPageUrl);
                window.location.href = detailPageUrl;
            }
        });
    }
}); 