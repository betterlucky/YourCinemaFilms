// Search functionality for YourCinemaFilms
document.addEventListener('DOMContentLoaded', function() {
    // Handle click on search results to navigate to film detail page
    document.addEventListener('click', function(e) {
        const searchResultLink = e.target.closest('.search-result-link');
        if (searchResultLink) {
            e.preventDefault();
            const filmId = searchResultLink.dataset.filmId;
            if (filmId) {
                const detailUrl = searchResultLink.getAttribute('href');
                if (detailUrl) {
                    window.location.href = detailUrl;
                }
            }
        }
    });
}); 