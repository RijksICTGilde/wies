// Auto-show dialog functionality based on PR #116 pattern
document.addEventListener('DOMContentLoaded', function() {
    // Find all dialogs with closedby="any" attribute
    const dialogs = document.querySelectorAll('dialog[closedby="any"]');
    
    dialogs.forEach(function(dialog) {
        // If dialog has content, show it automatically
        if (dialog.innerHTML.trim()) {
            dialog.showModal();
        }
        
        // Add close button listeners
        const closeButtons = dialog.querySelectorAll('.modal-close');
        closeButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                dialog.close();
            });
        });
    });
});

// Auto-open modal when HTMX loads content (for dynamic content)
document.addEventListener('htmx:afterSwap', function(e) {
    const dialog = e.detail.target.querySelector('dialog[closedby="any"]');
    if (dialog && dialog.innerHTML.trim()) {
        dialog.showModal();
    }
});