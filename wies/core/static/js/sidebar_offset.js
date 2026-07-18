// Dynamically set --sidebar-offset so the sticky sidebar max-height accounts
// for the header visible above the fold.
(function () {
  const sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;
  const update = () => {
    const rect = sidebar.getBoundingClientRect();
    const offset = Math.max(0, rect.top);
    document.documentElement.style.setProperty(
      "--sidebar-offset",
      offset + "px",
    );
  };
  update();
  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
})();
