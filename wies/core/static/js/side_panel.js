document.addEventListener('DOMContentLoaded', function() {

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