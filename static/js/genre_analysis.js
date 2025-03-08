/**
 * Genre Analysis JavaScript
 * 
 * This file contains all the JavaScript functionality for the genre analysis page,
 * including chart initialization and data loading.
 */

// Global chart instances
let genreChart = null;
let genreDistributionChart = null;

// Initialize charts when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing genre analysis page');
    
    // Show loading indicators for charts
    showLoadingIndicators();
    
    // Wait a short time to ensure DOM is fully rendered
    setTimeout(function() {
        // Initialize charts
        initializeCharts();
    }, 500);
});

/**
 * Show loading indicators for charts
 */
function showLoadingIndicators() {
    console.log('Showing loading indicators');
    
    const genreChartContainer = document.getElementById('genre-chart-container');
    const genresChartContainer = document.getElementById('genres-chart-container');
    
    if (genreChartContainer) {
        genreChartContainer.innerHTML = 
            '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading chart...</p></div>';
    }
    
    if (genresChartContainer) {
        genresChartContainer.innerHTML = 
            '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading chart...</p></div>';
    }
}

/**
 * Initialize the charts
 */
function initializeCharts() {
    console.log('Initializing charts');
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Loading it now...');
        loadChartJs();
        return;
    }
    
    // Get the selected genre and period
    const genreSelect = document.getElementById('genre-select');
    const periodSelect = document.getElementById('period-select');
    
    if (!genreSelect || !periodSelect) {
        console.error('Genre or period select elements not found');
        return;
    }
    
    const selectedGenre = genreSelect.value;
    const period = periodSelect.value;
    
    console.log('Selected genre:', selectedGenre, 'period:', period);
    
    // Load the appropriate chart
    if (selectedGenre) {
        loadGenreSpecificChart(selectedGenre, period);
    } else {
        loadGenreDistributionChart(period);
    }
    
    // Set up event listeners for the dropdowns
    setupEventListeners();
}

/**
 * Load Chart.js dynamically
 */
function loadChartJs() {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
    script.onload = function() {
        console.log('Chart.js loaded successfully');
        initializeCharts();
    };
    script.onerror = function() {
        console.error('Failed to load Chart.js');
        showChartLoadError();
    };
    document.head.appendChild(script);
}

/**
 * Show error message when Chart.js fails to load
 */
function showChartLoadError() {
    const genreChartContainer = document.getElementById('genre-chart-container');
    const genresChartContainer = document.getElementById('genres-chart-container');
    
    if (genreChartContainer) {
        genreChartContainer.innerHTML = 
            '<div class="alert alert-warning">Unable to load chart library. Please refresh the page or try again later.</div>';
    }
    
    if (genresChartContainer) {
        genresChartContainer.innerHTML = 
            '<div class="alert alert-warning">Unable to load chart library. Please refresh the page or try again later.</div>';
    }
}

/**
 * Set up event listeners for the dropdowns
 */
function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // Listen for HTMX after swap event
    document.body.addEventListener('htmx:afterSwap', function(event) {
        console.log('HTMX content swapped, target:', event.detail.target.id);
        
        // Only reinitialize if the genre content was swapped
        if (event.detail.target.id === 'genre-content') {
            console.log('Genre content was swapped, reinitializing charts');
            
            // Get the selected genre and period
            const genreSelect = document.getElementById('genre-select');
            const periodSelect = document.getElementById('period-select');
            
            if (!genreSelect || !periodSelect) {
                console.error('Genre or period select elements not found after swap');
                return;
            }
            
            const selectedGenre = genreSelect.value;
            const period = periodSelect.value;
            
            console.log('After swap detected genre:', selectedGenre, 'period:', period);
            
            // Initialize the appropriate chart
            setTimeout(function() {
                if (selectedGenre) {
                    loadGenreSpecificChart(selectedGenre, period);
                } else {
                    loadGenreDistributionChart(period);
                }
            }, 100); // Small delay to ensure DOM is updated
        }
    });
    
    // These are handled by HTMX, but we'll add them here for completeness
    const genreSelect = document.getElementById('genre-select');
    const periodSelect = document.getElementById('period-select');
    
    if (genreSelect) {
        genreSelect.addEventListener('change', function() {
            console.log('Genre changed to:', this.value);
        });
    }
    
    if (periodSelect) {
        periodSelect.addEventListener('change', function() {
            console.log('Period changed to:', this.value);
        });
    }
}

/**
 * Load the genre-specific chart
 */
function loadGenreSpecificChart(genre, period) {
    console.log('Loading genre-specific chart for:', genre, 'period:', period);
    
    const chartContainer = document.getElementById('genre-chart-container');
    if (!chartContainer) {
        console.error('Genre chart container not found');
        return;
    }
    
    // Show loading indicator
    chartContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading chart data...</p></div>';
    
    // Make the AJAX request
    $.ajax({
        url: '/api/charts/data/',
        data: { 
            genre: genre,
            period: period
        },
        success: function(response) {
            console.log('Chart data received:', response);
            
            // Check if we have valid data
            if (response && response.labels && response.labels.length > 0) {
                try {
                    // Get the canvas context
                    chartContainer.innerHTML = '<canvas id="genre-chart"></canvas>';
                    const canvas = document.getElementById('genre-chart');
                    const ctx = canvas.getContext('2d');
                    
                    // Destroy existing chart if it exists
                    if (genreChart) {
                        genreChart.destroy();
                    }
                    
                    // Create the new chart
                    genreChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: response.labels,
                            datasets: [{
                                label: 'Number of Votes',
                                data: response.data,
                                backgroundColor: 'rgba(13, 110, 253, 0.7)',
                                borderColor: 'rgba(13, 110, 253, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        precision: 0
                                    }
                                }
                            },
                            plugins: {
                                legend: {
                                    display: false
                                },
                                title: {
                                    display: true,
                                    text: 'Top ' + genre + ' Films by Votes'
                                }
                            }
                        }
                    });
                    
                    console.log('Genre chart created successfully');
                } catch (error) {
                    console.error('Error creating chart:', error);
                    chartContainer.innerHTML = '<div class="alert alert-danger">Error creating chart. Please try again later.</div>';
                }
            } else {
                console.log('No data available for chart');
                chartContainer.innerHTML = '<div class="alert alert-info">No data available for this genre and time period.</div>';
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', status, error);
            chartContainer.innerHTML = '<div class="alert alert-danger">Error loading chart data. Please try again later.</div>';
        }
    });
}

/**
 * Load the genre distribution chart
 */
function loadGenreDistributionChart(period) {
    console.log('Loading genre distribution chart for period:', period);
    
    const chartContainer = document.getElementById('genres-chart-container');
    if (!chartContainer) {
        console.error('Genres chart container not found');
        return;
    }
    
    // Show loading indicator
    chartContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading chart data...</p></div>';
    
    // Make the AJAX request
    $.ajax({
        url: '/api/genres/data/',
        data: { period: period },
        success: function(response) {
            console.log('Genre distribution data received:', response);
            
            // Check if we have valid data
            if (response && response.labels && response.labels.length > 0) {
                try {
                    // Get the canvas context
                    chartContainer.innerHTML = '<canvas id="genres-chart"></canvas>';
                    const canvas = document.getElementById('genres-chart');
                    const ctx = canvas.getContext('2d');
                    
                    // Destroy existing chart if it exists
                    if (genreDistributionChart) {
                        genreDistributionChart.destroy();
                    }
                    
                    // Create the new chart
                    genreDistributionChart = new Chart(ctx, {
                        type: 'pie',
                        data: {
                            labels: response.labels,
                            datasets: [{
                                data: response.data,
                                backgroundColor: response.labels.map((_, i) => getColorForIndex(i, 0.7)),
                                borderColor: response.labels.map((_, i) => getColorForIndex(i, 1)),
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'right',
                                    labels: {
                                        boxWidth: 15
                                    }
                                },
                                title: {
                                    display: true,
                                    text: 'Genre Distribution by Votes'
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${label}: ${value} votes (${percentage}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                    
                    console.log('Genre distribution chart created successfully');
                } catch (error) {
                    console.error('Error creating chart:', error);
                    chartContainer.innerHTML = '<div class="alert alert-danger">Error creating chart. Please try again later.</div>';
                }
            } else {
                console.log('No data available for chart');
                chartContainer.innerHTML = '<div class="alert alert-info">No data available for this time period.</div>';
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', status, error);
            chartContainer.innerHTML = '<div class="alert alert-danger">Error loading chart data. Please try again later.</div>';
        }
    });
}

/**
 * Helper function to get colors for datasets
 */
function getColorForIndex(index, alpha) {
    const colors = [
        `rgba(0, 123, 255, ${alpha})`,     // Blue
        `rgba(220, 53, 69, ${alpha})`,     // Red
        `rgba(40, 167, 69, ${alpha})`,     // Green
        `rgba(255, 193, 7, ${alpha})`,     // Yellow
        `rgba(111, 66, 193, ${alpha})`,    // Purple
        `rgba(253, 126, 20, ${alpha})`,    // Orange
        `rgba(23, 162, 184, ${alpha})`,    // Cyan
        `rgba(102, 16, 242, ${alpha})`,    // Indigo
        `rgba(32, 201, 151, ${alpha})`,    // Teal
        `rgba(52, 58, 64, ${alpha})`       // Dark gray
    ];
    
    return colors[index % colors.length];
} 