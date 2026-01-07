// Function to setup dialog event listeners
function setupDialogListeners(container) {
    container = container || document;
    
    const dialogs = container.querySelectorAll('dialog[closedby="any"]');
    
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
}

// Setup dialogs on page load
document.addEventListener('DOMContentLoaded', function() {
    setupDialogListeners();
});

// Auto-open modal when HTMX loads content (for dynamic content)
document.addEventListener('htmx:afterSwap', function(e) {
    // Setup dialogs in the swapped content
    setupDialogListeners(e.detail.target);
    
    // Close modals when category blocks are swapped
    if (e.detail.target.id && e.detail.target.id.startsWith('label_category_')) {
        const modal = document.getElementById("labelFormModal");
        if (modal) {
            modal.innerHTML = '';
        }
    }
});