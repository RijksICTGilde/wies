// Client page functionality
function initializeClientToggles() {
    // This function will be called after the page loads to set up toggle functions
    // The toggle functions are dynamically created based on the ministries present
}

// Function to create toggle functionality for a specific ministry
function createMinistryToggle(ministryIndex) {
    return function() {
        const hiddenItems = document.querySelectorAll('.ministry-' + ministryIndex + '-org.hidden');
        const button = document.getElementById('ministry-' + ministryIndex + '-toggle');
        
        if (hiddenItems.length > 0) {
            hiddenItems.forEach(item => item.classList.remove('hidden'));
            button.textContent = 'Toon minder opdrachtgevers';
        } else {
            const allItems = document.querySelectorAll('.ministry-' + ministryIndex + '-org');
            allItems.forEach((item, index) => {
                if (index >= 3) item.classList.add('hidden');
            });
            button.textContent = 'Toon meer opdrachtgevers';
        }
    };
}