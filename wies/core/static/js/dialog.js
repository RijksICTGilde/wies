// HTMX + Dialog integration - hybrid approach
document.addEventListener('htmx:afterSwap', function(e) {
    // When HTMX loads modal content into a container, find any dialogs and show them
    const dialogs = e.detail.target.querySelectorAll('dialog[closedby="any"]');
    
    dialogs.forEach(function(dialog) {
        // Auto-show dialog when HTMX loads content
        if (dialog.innerHTML.trim()) {
            dialog.showModal();
        }
        
        // Add close button listeners for .close elements (PR #116 style)
        const closeElements = dialog.querySelectorAll('.close');
        closeElements.forEach(function(element) {
            element.addEventListener('click', function() {
                dialog.close();
            });
        });
    });
    
    // Close modals when category blocks are swapped (label admin specific)
    if (e.detail.target.id && e.detail.target.id.startsWith('label_category_')) {
        const modal = document.getElementById("labelFormModal");
        if (modal) {
            modal.innerHTML = '';
        }
    }
    
});

// Handle static filter modal (not loaded via HTMX)
document.addEventListener('DOMContentLoaded', function() {
    const filterModal = document.getElementById('filterModal');
    if (filterModal) {
        // Add close button listeners for all buttons in filter modal
        const closeButtons = filterModal.querySelectorAll('button, c-button');
        closeButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                // Only close for close buttons (not form submit buttons)
                if (button.classList.contains('modal-close-button') || 
                    button.closest('.close')) {
                    e.preventDefault();
                    e.stopPropagation();
                    filterModal.close();
                }
            });
        });
        
        // ESC key handler
        filterModal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                filterModal.close();
            }
        });
    }
});

