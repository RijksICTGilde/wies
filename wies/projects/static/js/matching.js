// WIES Matching Kanban Board JavaScript
document.addEventListener('DOMContentLoaded', function() {
    let draggedElement = null;
    let draggedData = null;

    // Initialize drag and drop functionality
    initializeDragAndDrop();

    function initializeDragAndDrop() {
        // Make all cards draggable
        document.querySelectorAll('.wies-kanban-card[draggable="true"]').forEach(card => {
            card.addEventListener('dragstart', handleDragStart);
            card.addEventListener('dragend', handleDragEnd);
        });

        // Make columns droppable
        document.querySelectorAll('.wies-kanban-column').forEach(column => {
            column.addEventListener('dragover', handleDragOver);
            column.addEventListener('dragleave', handleDragLeave);
            column.addEventListener('drop', handleDrop);
        });
    }

    function handleDragStart(e) {
        draggedElement = this;
        draggedData = {
            type: this.dataset.type,
            id: this.dataset.id
        };
        this.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    }

    function handleDragEnd(e) {
        this.classList.remove('dragging');
        draggedElement = null;
        draggedData = null;
        
        // Remove drag-over class from all columns
        document.querySelectorAll('.wies-kanban-column').forEach(col => {
            col.classList.remove('drag-over');
        });
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        this.classList.add('drag-over');
    }

    function handleDragLeave(e) {
        // Check if we really left the column (not just a child element)
        if (!this.contains(e.relatedTarget)) {
            this.classList.remove('drag-over');
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        
        if (!draggedElement || !draggedData) return;

        const targetColumn = this.dataset.column;
        const cardsContainer = this.querySelector('.wies-kanban-cards');
        
        // Determine which actions are allowed
        const sourceColumn = draggedElement.closest('.wies-kanban-column').dataset.column;
        
        if (sourceColumn === targetColumn) {
            return; // No action needed
        }

        // Update assignment status
        handleStatusChange(draggedData, targetColumn);
        
        // Move card visually
        cardsContainer.appendChild(draggedElement);
        
        // Update counters
        updateColumnCounts();
        
        // Trigger HTMX event for backend update
        triggerBackendUpdate(draggedData.id, targetColumn);
    }

    function handleStatusChange(draggedData, targetColumn) {
        console.log('Status wijzigen van opdracht:', draggedData.id, 'naar:', targetColumn);
    }

    function updateColumnCounts() {
        document.querySelectorAll('.wies-kanban-column').forEach(column => {
            const count = column.querySelectorAll('.wies-kanban-card').length;
            const countElement = column.querySelector('.rvo-badge');
            if (countElement) {
                countElement.textContent = count;
            }
        });
    }

    function triggerBackendUpdate(assignmentId, statusId) {
        const form = document.querySelector('#assignmentMovedForm');
        if (form) {
            const assignmentIdInput = form.querySelector('input[name="assignmentId"]');
            const statusIdInput = form.querySelector('input[name="statusId"]');
            
            if (assignmentIdInput) assignmentIdInput.value = assignmentId;
            if (statusIdInput) statusIdInput.value = statusId;
            
            // Trigger HTMX event
            if (typeof htmx !== 'undefined') {
                htmx.trigger('#assignmentMovedForm', 'assignmentmoved');
            }
        }
    }

    // Global function for opening assignment details
    window.openAssignment = function(assignmentId) {
        window.location.href = '/assignments/' + assignmentId + '/';
    };
});