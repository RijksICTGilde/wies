// Organisation admin: chevron toggle and search within the nldd-list tree.
// Nesting is real DOM nesting (child rows sit in the parent's
// slot="children"), so ancestors come from closest('nldd-list-item') chains.
(function () {
  "use strict";

  var input = document.getElementById("org-search");
  var root = document.getElementById("org-tree-root");
  if (!input || !root) return;

  var allItems = Array.prototype.slice.call(
    root.querySelectorAll("nldd-list-item"),
  );
  var savedState = null; // Map<item, boolean> — expanded state before search
  var isSearching = false;

  // nldd-list-item announces its expanded state but does not toggle it. The
  // innermost row in the composedPath wins, so a child cannot expand its parent.
  root.addEventListener("click", function (e) {
    var row = window.wiesClosestInPath(e, "nldd-list-item[button]");
    if (!row) return;
    row.toggleAttribute("expanded", !row.hasAttribute("expanded"));
  });

  function saveExpandedState() {
    savedState = new Map();
    allItems.forEach(function (item) {
      savedState.set(item, item.hasAttribute("expanded"));
    });
  }

  function restoreExpandedState() {
    if (!savedState) return;
    savedState.forEach(function (wasExpanded, item) {
      item.toggleAttribute("expanded", wasExpanded);
    });
    savedState = null;
  }

  function matches(item, query) {
    var label = item.getAttribute("data-label") || "";
    if (label.indexOf(query) !== -1) return true;
    var abbr = item.getAttribute("data-abbr") || "";
    return abbr.indexOf(query) !== -1;
  }

  function showAncestors(item) {
    var el = item.parentElement && item.parentElement.closest("nldd-list-item");
    while (el) {
      el.hidden = false;
      el.setAttribute("expanded", "");
      el = el.parentElement && el.parentElement.closest("nldd-list-item");
    }
  }

  function showDescendants(item) {
    item.querySelectorAll("nldd-list-item").forEach(function (child) {
      child.hidden = false;
    });
  }

  // nldd-text-cell marks the match itself when `query` is set.
  function setHighlight(query) {
    root.querySelectorAll("nldd-text-cell").forEach(function (cell) {
      if (query) {
        cell.setAttribute("query", query);
        cell.setAttribute("query-mark-mode", "match");
      } else {
        cell.removeAttribute("query");
      }
    });
  }

  function filterTree(query) {
    if (!query) {
      isSearching = false;
      allItems.forEach(function (item) {
        item.hidden = false;
      });
      setHighlight("");
      restoreExpandedState();
      return;
    }

    if (!isSearching) {
      saveExpandedState();
      isSearching = true;
    }

    allItems.forEach(function (item) {
      item.hidden = true;
    });

    allItems.forEach(function (item) {
      if (item.hasAttribute("data-org-group")) return; // groups shown via ancestors
      if (matches(item, query)) {
        item.hidden = false;
        showAncestors(item);
        showDescendants(item);
      }
    });

    setHighlight(query);
    // With every row [hidden] the list shows its own empty state.
  }

  var timer = null;
  input.addEventListener("input", function (e) {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var raw =
        e.detail && e.detail.value !== undefined
          ? e.detail.value
          : input.value || "";
      filterTree(String(raw).toLowerCase().trim());
    }, 150);
  });
})();
