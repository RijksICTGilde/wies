document.addEventListener('DOMContentLoaded', function() {

  // Set body overflow when panel is present (like filter modal)
  const panelContainer = document.getElementById('side_panel-container');
  if (panelContainer && panelContainer.innerHTML.trim()) {
    document.body.style.overflow = 'hidden';
  } else {
    // Reset overflow if no panel is present (important for back button)
    document.body.style.overflow = 'auto';
  }

  // Handle ESC key to close panel
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      const panel = document.getElementById('side_panel-overlay');
      if (panel) {
        const closeBtn = panel.querySelector('.rvo-dialog__close a');
        if (closeBtn) {
          closeBtn.click();
        }
      }
    }
  });

  // Handle background click to close panel (like RVO dialogs)
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('rvo-dialog__background')) {
      const closeBtn = e.target.querySelector('.rvo-dialog__close a');
      if (closeBtn) {
        closeBtn.click();
      }
    }
  });
});