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

/* LLM Search Functions */
async function performLLMSearch(searchQuery) {
  const llmResponseContainer = document.getElementById('llm-response-container');
  const llmResponseContent = document.getElementById('llm-response-content');
  const llmLoadingIndicator = document.getElementById('llm-loading-indicator');
  const traditionalResultsSection = document.getElementById('traditional-results-section');

  if (!llmResponseContainer) return; // Not on search results page

  // Show loading state, hide traditional results
  llmResponseContainer.style.display = 'block';
  llmLoadingIndicator.style.display = 'block';
  llmResponseContent.style.display = 'none';
  llmResponseContent.innerHTML = '';

  try {
    const searchParams = new URLSearchParams();
    searchParams.set('search', searchQuery);

    const response = await fetch(`/api/llm-search/?${searchParams.toString()}`);
    const data = await response.json();

    // Hide loading indicator
    llmLoadingIndicator.style.display = 'none';

    if (data.success && data.response) {
      // Display LLM response (already HTML from server)
      llmResponseContent.innerHTML = data.response;
      llmResponseContent.style.display = 'block';

      // Show traditional results after LLM completes
      if (traditionalResultsSection) {
        traditionalResultsSection.style.display = 'block';
      }
    } else if (data.user_message) {
      // Display user-friendly error message (plain text, needs escaping)
      llmResponseContent.innerHTML = `<p class="rvo-paragraph rvo-text--subtle">${escapeHtml(data.user_message)}</p>`;
      llmResponseContent.style.display = 'block';

      // Show traditional results even on error
      if (traditionalResultsSection) {
        traditionalResultsSection.style.display = 'block';
      }
    } else {
      // Hide LLM container on unexpected error
      llmResponseContainer.style.display = 'none';

      // Show traditional results as fallback
      if (traditionalResultsSection) {
        traditionalResultsSection.style.display = 'block';
      }
      console.error('LLM search unexpected response format:', data);
    }
  } catch (error) {
    // Hide LLM container on network error
    llmResponseContainer.style.display = 'none';

    // Show traditional results as fallback
    if (traditionalResultsSection) {
      traditionalResultsSection.style.display = 'block';
    }
    console.error('LLM search request failed:', error);
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
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

  // Trigger LLM search on search results page
  const urlParams = new URLSearchParams(window.location.search);
  const searchQuery = urlParams.get('search');
  if (searchQuery && document.getElementById('llm-response-container')) {
    performLLMSearch(searchQuery);
  }
});