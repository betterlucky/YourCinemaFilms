/**
 * Genre Analysis JavaScript
 * 
 * This file contains all the JavaScript functionality for the genre analysis page,
 * including chart initialization, genre comparison, and export functionality.
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
                                backgroundColor: [
                                    'rgba(0, 123, 255, 0.7)',    // Blue
                                    'rgba(220, 53, 69, 0.7)',    // Red
                                    'rgba(40, 167, 69, 0.7)',    // Green
                                    'rgba(255, 193, 7, 0.7)',    // Yellow
                                    'rgba(111, 66, 193, 0.7)',   // Purple
                                    'rgba(253, 126, 20, 0.7)',   // Orange
                                    'rgba(23, 162, 184, 0.7)',   // Cyan
                                    'rgba(102, 16, 242, 0.7)',   // Indigo
                                    'rgba(32, 201, 151, 0.7)',   // Teal
                                    'rgba(52, 58, 64, 0.7)'      // Dark gray
                                ],
                                borderColor: [
                                    'rgba(0, 123, 255, 1)',
                                    'rgba(220, 53, 69, 1)',
                                    'rgba(40, 167, 69, 1)',
                                    'rgba(255, 193, 7, 1)',
                                    'rgba(111, 66, 193, 1)',
                                    'rgba(253, 126, 20, 1)',
                                    'rgba(23, 162, 184, 1)',
                                    'rgba(102, 16, 242, 1)',
                                    'rgba(32, 201, 151, 1)',
                                    'rgba(52, 58, 64, 1)'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'right'
                                },
                                title: {
                                    display: true,
                                    text: 'Genre Distribution of Voted Films'
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${label}: ${value} films (${percentage}%)`;
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
                chartContainer.innerHTML = '<div class="alert alert-info">No genre data available for this time period.</div>';
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', status, error);
            chartContainer.innerHTML = '<div class="alert alert-danger">Error loading chart data. Please try again later.</div>';
        }
    });
}

/**
 * Initialize the genre comparison functionality
 */
function initGenreComparison() {
    let comparisonChart = null;
    
    // Handle genre comparison button click
    const compareButton = document.getElementById('compare-genres-btn');
    if (compareButton) {
        compareButton.addEventListener('click', function() {
            const selectedGenres = [];
            document.querySelectorAll('.genre-compare-checkbox:checked').forEach(function(checkbox) {
                selectedGenres.push(checkbox.value);
            });
            
            if (selectedGenres.length === 0) {
                alert('Please select at least one genre to compare');
                return;
            }
            
            // Show loading indicator
            const chartContainer = document.getElementById('comparison-chart-container');
            chartContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading comparison data...</p></div>';
            
            // Get the current period
            const period = document.getElementById('period-select').value;
            
            // Fetch data for each genre
            const promises = selectedGenres.map(genre => {
                return $.ajax({
                    url: '/api/charts/data/',
                    data: { 
                        genre: genre,
                        period: period
                    }
                });
            });
            
            Promise.all(promises)
                .then(results => {
                    // Process results
                    const datasets = [];
                    const allLabels = new Set();
                    
                    // Get all unique film labels
                    results.forEach(result => {
                        result.labels.forEach(label => allLabels.add(label));
                    });
                    
                    // Convert to array and sort alphabetically
                    const labels = Array.from(allLabels).sort();
                    
                    // Create a dataset for each genre
                    results.forEach((result, index) => {
                        const data = new Array(labels.length).fill(0);
                        
                        // Map the data to the correct positions
                        result.labels.forEach((label, i) => {
                            const labelIndex = labels.indexOf(label);
                            if (labelIndex !== -1) {
                                data[labelIndex] = result.data[i];
                            }
                        });
                        
                        datasets.push({
                            label: selectedGenres[index],
                            data: data,
                            backgroundColor: getColorForIndex(index, 0.7),
                            borderColor: getColorForIndex(index, 1),
                            borderWidth: 1
                        });
                    });
                    
                    // Create the comparison chart
                    const ctx = chartContainer.getContext('2d');
                    
                    if (comparisonChart) {
                        comparisonChart.destroy();
                    }
                    
                    comparisonChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: datasets
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
                                title: {
                                    display: true,
                                    text: 'Genre Comparison by Film Votes'
                                }
                            }
                        }
                    });
                    
                    // Enable export button
                    document.getElementById('export-comparison-btn').disabled = false;
                })
                .catch(error => {
                    console.error('Error fetching comparison data:', error);
                    chartContainer.innerHTML = '<div class="alert alert-danger">Error loading comparison data. Please try again later.</div>';
                });
        });
    }
    
    // Make the comparison chart available globally for export
    window.getComparisonChart = function() {
        return comparisonChart;
    };
}

/**
 * Initialize the export functionality
 */
function initExportFunctionality() {
    // Handle export button click
    const exportButton = document.getElementById('export-comparison-btn');
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            const exportModal = new bootstrap.Modal(document.getElementById('exportModal'));
            exportModal.show();
        });
    }
    
    // Handle actual export
    const doExportButton = document.getElementById('do-export-btn');
    if (doExportButton) {
        doExportButton.addEventListener('click', function() {
            const format = document.getElementById('export-format').value;
            const chartType = document.getElementById('export-chart').value;
            
            let chartToExport;
            if (chartType === 'comparison') {
                chartToExport = window.getComparisonChart();
            } else {
                // Find the current visible chart
                if (document.getElementById('genre-chart-container') && 
                    document.getElementById('genre-chart-container').offsetParent !== null) {
                    chartToExport = Chart.getChart(document.getElementById('genre-chart-container'));
                } else if (document.getElementById('genres-chart-container')) {
                    chartToExport = Chart.getChart(document.getElementById('genres-chart-container'));
                }
            }
            
            if (!chartToExport) {
                alert('No chart available to export');
                return;
            }
            
            if (format === 'png') {
                // Export as PNG
                const url = chartToExport.toBase64Image();
                const link = document.createElement('a');
                link.download = 'genre-analysis-chart.png';
                link.href = url;
                link.click();
            } else if (format === 'csv') {
                // Export as CSV
                const data = chartToExport.data;
                let csv = 'Label,';
                
                // Add dataset labels as header
                data.datasets.forEach((dataset, i) => {
                    csv += dataset.label || `Dataset ${i+1}`;
                    if (i < data.datasets.length - 1) csv += ',';
                });
                csv += '\n';
                
                // Add data rows
                data.labels.forEach((label, i) => {
                    csv += `"${label}",`;
                    data.datasets.forEach((dataset, j) => {
                        csv += dataset.data[i];
                        if (j < data.datasets.length - 1) csv += ',';
                    });
                    csv += '\n';
                });
                
                const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
                saveAs(blob, 'genre-analysis-data.csv');
            } else if (format === 'json') {
                // Export as JSON
                const data = chartToExport.data;
                const jsonData = {
                    labels: data.labels,
                    datasets: data.datasets.map(dataset => ({
                        label: dataset.label,
                        data: dataset.data
                    }))
                };
                
                const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
                saveAs(blob, 'genre-analysis-data.json');
            }
            
            bootstrap.Modal.getInstance(document.getElementById('exportModal')).hide();
        });
    }
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