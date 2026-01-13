document.addEventListener('DOMContentLoaded', function() {

  // Set body overflow when panel is present (like filter modal)
  const panelContainer = document.getElementById('side_panel-container');
  if (panelContainer && panelContainer.innerHTML.trim()) {
    document.body.style.overflow = 'hidden';
    
    // Use showModal() for consistency with other modals
    const panel = document.getElementById('side_panel');
    if (panel) {
      panel.showModal();
      
      // Handle ESC key to close panel completely
      panel.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          e.preventDefault(); // Prevent default dialog close
          // Get current URL and remove only colleague/assignment params, keep filters
          const url = new URL(window.location);
          url.searchParams.delete('colleague');
          url.searchParams.delete('assignment');
          // Navigate to URL without panel params but with all filters intact
          window.location.href = url.toString();
        }
      });
    }
  } else {
    // Reset overflow if no panel is present (important for back button)
    document.body.style.overflow = 'auto';
  }


  // Handle background click to close panel (dialog backdrop click)
  document.addEventListener('click', function(e) {
    const panel = document.getElementById('side_panel');
    if (panel && e.target === panel) {
      // Clicked on dialog backdrop
      const closeBtn = panel.querySelector('.modal-close-button');
      if (closeBtn) {
        closeBtn.click();
      }
    }
  });

});