document.addEventListener("DOMContentLoaded", function () {
  // Set body overflow when panel is present (like filter modal)
  const panelContainer = document.getElementById("side_panel-container");
  if (panelContainer && panelContainer.innerHTML.trim()) {
    document.body.style.overflow = "hidden";

    // Use showModal() for consistency with other modals
    const panel = document.getElementById("side_panel");
    if (panel) {
      panel.showModal();

      // Trigger animation after a tiny delay to ensure initial state is rendered
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          panel.classList.add("opening");
        });
      });
    }
  } else {
    // Reset overflow if no panel is present (important for back button)
    document.body.style.overflow = "auto";
  }

  // Close panel with filter preservation
  function closePanelWithFilters() {
    const panel = document.getElementById("side_panel");
    if (panel) {
      // Add closing class for animation
      panel.classList.add("closing");

      // Wait for animation to finish before navigating
      setTimeout(() => {
        const url = new URL(window.location);
        url.searchParams.delete("collega");
        url.searchParams.delete("opdracht");
        window.location.href = url.toString();
      }, 400); // Match transition duration in CSS
    } else {
      // Fallback if panel doesn't exist
      const url = new URL(window.location);
      url.searchParams.delete("collega");
      url.searchParams.delete("opdracht");
      window.location.href = url.toString();
    }
  }

  // Handle close button clicks
  const panel = document.getElementById("side_panel");
  if (panel) {
    const closeBtn = panel.querySelector(".modal-close-button");
    if (closeBtn) {
      closeBtn.addEventListener("click", function (e) {
        e.preventDefault();
        closePanelWithFilters();
      });
    }
  }

  // Handle background click to close panel (dialog backdrop click)
  document.addEventListener("click", function (e) {
    const panel = document.getElementById("side_panel");
    if (panel && e.target === panel) {
      closePanelWithFilters();
    }
  });
});
