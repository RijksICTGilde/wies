// WIES Search Functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeSearchField();
    initializeSearchForm();
});

function initializeSearchField() {
    // Set search field value if there's a search parameter
    const urlParams = new URLSearchParams(window.location.search);
    const searchValue = urlParams.get('search');
    
    if (searchValue) {
        const searchField = document.getElementById('globalSearchField');
        if (searchField) {
            searchField.value = searchValue;
        }
    }
}

function initializeSearchForm() {
    // Add enter key support for search
    const searchField = document.getElementById('globalSearchField');
    if (searchField) {
        searchField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performGlobalSearch();
            }
        });
    }
}

function performGlobalSearch() {
    const searchField = document.getElementById('globalSearchField');
    if (searchField) {
        const searchValue = searchField.value.trim();
        if (searchValue) {
            window.location.href = '/search/?search=' + encodeURIComponent(searchValue);
        } else {
            // If search is empty, go to search page without query
            window.location.href = '/search/';
        }
    }
}

function toggleSearchForm(event) {
    event.preventDefault();
    const searchFormSection = document.getElementById('searchFormSection');
    if (searchFormSection) {
        const isVisible = searchFormSection.style.display !== 'none';
        searchFormSection.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            // Focus on search field when showing
            const searchField = document.getElementById('globalSearchField');
            if (searchField) {
                setTimeout(() => searchField.focus(), 100);
            }
        }
    }
}