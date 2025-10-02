/**
 * Global Search Functionality
 * Handles menu search and search results interactions
 */

/* Menu Search Functions */
function toggleSearchForm(event) {
  event.preventDefault();
  const searchForm = document.getElementById('searchFormSection');
  const searchField = document.getElementById('globalSearchField');
  
  if (searchForm.style.display === 'none' || searchForm.style.display === '') {
    searchForm.style.display = 'block';
    // Focus on the search input when the form opens
    setTimeout(() => {
      searchField.focus();
    }, 100);
  } else {
    searchForm.style.display = 'none';
  }
}

function performGlobalSearch() {
  const searchTerm = document.getElementById('globalSearchField').value.trim();
  
  if (searchTerm === '') {
    alert('Voer een zoekterm in');
    return;
  }
  
  // Redirect to the global search results page
  const searchParams = new URLSearchParams();
  searchParams.set('search', searchTerm);
  
  window.location.href = `/search/?${searchParams.toString()}`;
}

/* Search Results Toggle Functions */
function toggleAssignments() {
  const hiddenItems = document.querySelectorAll('.assignment-item.hidden');
  const button = document.getElementById('assignments-toggle');
  
  if (hiddenItems.length > 0) {
    hiddenItems.forEach(item => item.classList.remove('hidden'));
    button.textContent = 'Toon minder resultaten';
  } else {
    const allItems = document.querySelectorAll('.assignment-item');
    allItems.forEach((item, index) => {
      if (index >= 3) item.classList.add('hidden');
    });
    button.textContent = 'Toon alle resultaten';
  }
}

function toggleColleagues() {
  const hiddenItems = document.querySelectorAll('.colleague-item.hidden');
  const button = document.getElementById('colleagues-toggle');
  
  if (hiddenItems.length > 0) {
    hiddenItems.forEach(item => item.classList.remove('hidden'));
    button.textContent = 'Toon minder resultaten';
  } else {
    const allItems = document.querySelectorAll('.colleague-item');
    allItems.forEach((item, index) => {
      if (index >= 3) item.classList.add('hidden');
    });
    button.textContent = 'Toon alle resultaten';
  }
}

function toggleMinistries() {
  const hiddenItems = document.querySelectorAll('.ministry-item.hidden');
  const button = document.getElementById('ministries-toggle');
  
  if (hiddenItems.length > 0) {
    hiddenItems.forEach(item => item.classList.remove('hidden'));
    button.textContent = 'Toon minder resultaten';
  } else {
    const allItems = document.querySelectorAll('.ministry-item');
    allItems.forEach((item, index) => {
      if (index >= 3) item.classList.add('hidden');
    });
    button.textContent = 'Toon alle resultaten';
  }
}

/* Initialize search functionality when DOM is loaded */
document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.querySelector('.rvo-menubar-search-input');
  const searchField = document.getElementById('globalSearchField');
  
  // Add smooth focus/blur animations for inline search (on search page)
  if (searchInput) {
    searchInput.addEventListener('focus', function() {
      this.parentElement.style.backgroundColor = 'rgba(255, 255, 255, 0.25)';
    });
    
    searchInput.addEventListener('blur', function() {
      this.parentElement.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
    });
  }
  
  // Allow Enter key to trigger search in dropdown form
  if (searchField) {
    searchField.addEventListener('keypress', function(event) {
      if (event.key === 'Enter') {
        performGlobalSearch();
      }
    });
  }
  
  // Close search form when clicking outside
  document.addEventListener('click', function(event) {
    const searchForm = document.getElementById('searchFormSection');
    const searchButton = event.target.closest('a[onclick*="toggleSearchForm"]');
    
    if (searchForm && searchForm.style.display === 'block' && !searchForm.contains(event.target) && !searchButton) {
      searchForm.style.display = 'none';
    }
  });
});