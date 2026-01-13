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
        const modalContainer = document.getElementById("labelFormModal");
        if (modalContainer) {
            const dialog = modalContainer.querySelector('dialog');
            if (dialog) {
                dialog.close();
            }
        }
    }
});

// Listen for closeModal trigger from server
document.addEventListener('closeModal', function() {
    const modalContainer = document.getElementById("labelFormModal");
    if (modalContainer) {
        const dialog = modalContainer.querySelector('dialog');
        if (dialog) {
            dialog.close();
        }
    }
});


