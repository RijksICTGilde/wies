// Organisatiebeheer: chevron-toggle en zoeken in de nldd-list-boom.
//
// Rows carry data-label / data-abbr (lowercased); nesting is real DOM nesting
// (child rows sit in the parent row's slot="children"), so ancestors are
// found by walking closest('nldd-list-item') chains.
(function () {
  "use strict";

  var input = document.getElementById("org-search");
  var root = document.getElementById("org-tree-root");
  var emptyMsg = document.getElementById("org-search-empty");
  if (!input || !root) return;

  var allItems = Array.prototype.slice.call(
    root.querySelectorAll("nldd-list-item"),
  );
  var savedState = null; // Map<item, boolean> — expanded state before search
  var isSearching = false;

  // De hele takrij is de knop; hij kondigt zijn staat aan maar zet hem niet om,
  // dat is werk van de consumer (net als bij de opdrachtgever-pickers). De
  // binnenste rij uit de composedPath wint, zodat een kindrij niet zijn ouder
  // openklapt.
  root.addEventListener("click", function (e) {
    var row = e.composedPath().find(function (el) {
      return (
        el instanceof Element &&
        el.localName === "nldd-list-item" &&
        el.hasAttribute("button")
      );
    });
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

  // nldd-text-cell marks the match itself when `query` is set, so highlighting
  // is a matter of handing it the search term instead of rewriting text nodes.
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
      emptyMsg.hidden = true;
      emptyMsg.style.display = "none";
      root.hidden = false;
      return;
    }

    if (!isSearching) {
      saveExpandedState();
      isSearching = true;
    }

    allItems.forEach(function (item) {
      item.hidden = true;
    });

    var hasMatch = false;
    allItems.forEach(function (item) {
      if (item.hasAttribute("data-org-group")) return; // groups shown via ancestors
      if (matches(item, query)) {
        hasMatch = true;
        item.hidden = false;
        showAncestors(item);
        showDescendants(item);
      }
    });

    setHighlight(query);

    emptyMsg.hidden = hasMatch;
    emptyMsg.style.display = hasMatch ? "none" : "";
    root.hidden = !hasMatch;
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
