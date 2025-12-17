// Simple sidepanel utilities for HTMX views
(function() {
  'use strict';
  
  // Initialize panel from URL on page load
  document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('colleague') || params.has('assignment')) {
      htmx.ajax('GET', window.location.href, {
        target: '#sidepanel-container', 
        swap: 'innerHTML'
      });
    }
  });
  
  // Close panel function for templates
  window.closeSidepanel = function() {
    document.getElementById('sidepanel-container')?.replaceChildren();
    // Remove only panel params from URL, keep filters
    const params = new URLSearchParams(window.location.search);
    params.delete('colleague');
    params.delete('assignment');
    const newUrl = '/placements/' + (params.toString() ? '?' + params.toString() : '');
    history.pushState(null, '', newUrl);
  };
  
  // Close panel on ESC - works with server-side rendering
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      const closeButton = document.querySelector('#sidepanel-overlay .rvo-dialog__close-button');
      if (closeButton) {
        closeButton.click();
      }
    }
  });
  
})();