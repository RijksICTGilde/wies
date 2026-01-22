// App Layout Functions

function toggleFilters() {
  const layout = document.getElementById("app-layout");
  const isMobile = window.innerWidth <= 1024;

  if (isMobile) {
    // Mobile: toggle full screen overlay
    layout.classList.toggle("app-layout--mobile-filters-open");
  } else {
    // Desktop: toggle collapsed state
    const isCollapsed = layout.classList.toggle("app-layout--collapsed");

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
