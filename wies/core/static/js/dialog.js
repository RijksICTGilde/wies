// Simple dialog auto-show and close handling - based on PR #116 pattern
document.addEventListener('DOMContentLoaded', function() {
    // Find all dialogs with closedby="any" attribute
    const dialogs = document.querySelectorAll('dialog[closedby="any"]');
    
    dialogs.forEach(function(dialog) {
        // If dialog has content (more than just the close button), show it automatically
        const content = dialog.querySelector('.modal-content');
        if (content) {
            dialog.showModal();
        }
        
        // Add close button listeners for elements with close class
        const closeElements = dialog.querySelectorAll('.close');
        closeElements.forEach(function(element) {
            element.addEventListener('click', function() {
                dialog.close();
            });
        });
    });
});