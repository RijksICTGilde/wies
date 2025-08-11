/**
 * Tab functionality for dashboard and other pages
 */
function showTab(tabName) {
  // Hide all tab contents
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.add('hidden');
  });
  
  // Remove active class from all tabs
  document.querySelectorAll('.rvo-tabs__item-link').forEach(link => {
    link.classList.remove('rvo-tabs__item-link--active', 'rvo-link--active');
  });
  
  // Show selected tab
  document.getElementById(tabName).classList.remove('hidden');
  
  // Add active class to clicked tab
  event.target.classList.add('rvo-tabs__item-link--active', 'rvo-link--active');
} 