// Layout Functions

function toggleMobileMenu() {
  const menubar = document.querySelector(".menubar");
  if (menubar) {
    menubar.classList.toggle("menubar--mobile-open");
  }
}

function toggleFilters() {
  const layout = document.getElementById("layout");
  const isMobile = window.innerWidth <= 800;

  if (isMobile) {
    // Mobile: toggle full screen overlay
    layout.classList.toggle("layout--mobile-filters-open");
  } else {
    // Desktop: toggle collapsed state
    const isCollapsed = layout.classList.toggle("layout--collapsed");

    // Update URL without page reload
    const url = new URL(window.location);
    if (isCollapsed) {
      url.searchParams.set("filters", "0");
    } else {
      url.searchParams.delete("filters");
    }
    history.replaceState({}, "", url);
  }
}

function openColleaguePanel(colleagueId) {
  const url = new URL(window.location);
  url.searchParams.delete("opdracht");
  url.searchParams.set("collega", colleagueId);
  window.location.href = url.toString();
}

function openAssignmentPanel(assignmentId) {
  const url = new URL(window.location);
  url.searchParams.set("opdracht", assignmentId);
  window.location.href = url.toString();
}

// Global ESC key handler - closes all overlays
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    // Close generic filter modal (admin pages)
    const filterModal = document.getElementById("filterModal");
    if (filterModal && filterModal.style.display === "flex") {
      filterModal.style.display = "none";
      document.body.style.overflow = "auto";
      return;
    }

    // Close side panel
    const sidePanel = document.getElementById("side_panel");
    if (sidePanel && sidePanel.open) {
      sidePanel.classList.add("closing");
      setTimeout(() => {
        const url = new URL(window.location);
        url.searchParams.delete("collega");
        url.searchParams.delete("opdracht");
        window.location.href = url.toString();
      }, 400);
      return;
    }

    // Close mobile placement filters
    const layout = document.getElementById("layout");
    if (layout && layout.classList.contains("layout--mobile-filters-open")) {
      layout.classList.remove("layout--mobile-filters-open");
      return;
    }

    // Close mobile menu
    const menubar = document.querySelector(".menubar");
    if (menubar && menubar.classList.contains("menubar--mobile-open")) {
      menubar.classList.remove("menubar--mobile-open");
      return;
    }
  }
});
