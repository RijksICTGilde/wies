document.addEventListener('DOMContentLoaded', function() {

  // Set body overflow when panel is present (like filter modal)
  const panelContainer = document.getElementById('side_panel-container');
  if (panelContainer && panelContainer.innerHTML.trim()) {
    document.body.style.overflow = 'hidden';
    
    // Use showModal() for proper focus trapping (like other modals)
    const panel = document.getElementById('side_panel');
    if (panel) {
      panel.showModal();
      
      // Handle ESC key to trigger proper close behavior (history.back)
      panel.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          e.preventDefault(); // Prevent default dialog close
          const closeBtn = panel.querySelector('.modal-close-button');
          if (closeBtn) {
            closeBtn.click(); // Trigger history.back()
          }
        }
      });
    }
  } else {
    // Reset overflow if no panel is present (important for back button)
    document.body.style.overflow = 'auto';
  }


  // Handle background click to close panel (like RVO dialogs)
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('rvo-dialog__background')) {
      const closeBtn = e.target.querySelector('.rvo-dialog__close button');
      if (closeBtn) {
        closeBtn.click();
      }
    }
  });

});