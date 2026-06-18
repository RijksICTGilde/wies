(function () {
  function toggleGroup(header) {
    const expanded = header.getAttribute("aria-expanded") !== "false";
    const next = !expanded;
    header.setAttribute("aria-expanded", String(next));

    let row = header.nextElementSibling;
    while (row && !row.hasAttribute("data-group-header")) {
      if (row.hasAttribute("data-group-member")) {
        if (next) {
          row.removeAttribute("hidden");
        } else {
          row.setAttribute("hidden", "");
        }
      }
      row = row.nextElementSibling;
    }
  }

  document.addEventListener("click", function (event) {
    const header = event.target.closest("[data-group-header]");
    if (!header) return;
    toggleGroup(header);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    const header = event.target.closest("[data-group-header]");
    if (!header || event.target !== header) return;
    event.preventDefault();
    toggleGroup(header);
  });
})();
