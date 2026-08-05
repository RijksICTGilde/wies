// Sidebar collapse toggle.
//
// The "Filters" button (#sidebar-toggle) drives the
// <nldd-sidebar-section>'s own sheet: the section renders the sidebar as a
// sticky aside on wide screens and collapses it to a left sheet when narrower.
(function () {
  "use strict";

  function sidebarSection() {
    return document.querySelector("nldd-sidebar-section");
  }

  function toggleSidebar() {
    const section = sidebarSection();
    if (section && typeof section.toggle === "function") section.toggle();
  }

  function showSidebar() {
    const section = sidebarSection();
    if (section && typeof section.show === "function") section.show();
  }

  document.addEventListener("click", (e) => {
    const btn = e
      .composedPath()
      .find((el) => el instanceof Element && el.id === "sidebar-toggle");
    if (!btn) return;
    toggleSidebar();
  });

  // Hetzelfde vanuit het overflowmenu van de toolbar. Dat menu toont een KLOON
  // van het menu-item en meldt de keuze terug als select op het origineel, dus
  // een klik bereikt dit element nooit.
  //
  // De kloon houdt het id, dus zonder deze check vuurt dit twee keer: eerst op
  // de kloon in de shadow root van de toolbar, dan op het origineel. De sidebar
  // ging dan open en meteen weer dicht. document.contains is precies het
  // verschil: een node in een shadow root zit niet in de documentboom.
  document.addEventListener("select", (e) => {
    const item = e
      .composedPath()
      .find((el) => el instanceof Element && el.id === "sidebar-toggle-menu-item");
    if (!item || !document.contains(item)) return;
    // show() en geen toggle(): een keuze uit een menu is geen schakelaar. De
    // zichtbare Filter-knop mag togglen, want die staat ernaast en je ziet zijn
    // staat; een menu-item kies je om het paneel te openen, en toggle() sloot
    // het meteen weer zodra de sectie dacht dat het al openstond.
    showSidebar();
  });
})();
