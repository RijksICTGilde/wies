(function () {
  "use strict";

  var input = document.getElementById("org-search");
  var root = document.getElementById("org-tree-root");
  var emptyMsg = document.getElementById("org-search-empty");
  if (!input || !root) return;

  var allItems = root.querySelectorAll(".org-tree__item");
  var savedState = null; // Map<details, boolean> — open state before search
  var isSearching = false;

  function saveOpenState() {
    savedState = new Map();
    root.querySelectorAll("details").forEach(function (d) {
      savedState.set(d, d.open);
    });
  }

  function restoreOpenState() {
    if (!savedState) return;
    savedState.forEach(function (wasOpen, d) {
      d.open = wasOpen;
    });
    savedState = null;
  }

  function matches(item, query) {
    var label = item.getAttribute("data-label") || "";
    if (label.indexOf(query) !== -1) return true;
    var abbr = item.getAttribute("data-abbr") || "";
    if (abbr.indexOf(query) !== -1) return true;
    return false;
  }

  function showAncestors(item) {
    var el = item.parentElement;
    while (el && el !== root) {
      if (el.classList && el.classList.contains("org-tree__item")) {
        el.classList.remove("org-tree__item--hidden");
        // Open the details so the match is visible
        var details = el.querySelector(":scope > .org-tree__details");
        if (details) details.open = true;
      }
      el = el.parentElement;
    }
  }

  function showDescendants(item) {
    var children = item.querySelectorAll(".org-tree__item");
    for (var i = 0; i < children.length; i++) {
      children[i].classList.remove("org-tree__item--hidden");
    }
  }

  function filterTree(query) {
    if (!query) {
      // Clear search: show everything, restore state
      isSearching = false;
      allItems.forEach(function (item) {
        item.classList.remove("org-tree__item--hidden");
      });
      // Remove highlights
      root.querySelectorAll("mark").forEach(function (m) {
        var parent = m.parentNode;
        parent.replaceChild(document.createTextNode(m.textContent), m);
        parent.normalize();
      });
      restoreOpenState();
      emptyMsg.style.display = "none";
      root.style.display = "";
      return;
    }

    // Save state on first search keystroke
    if (!isSearching) {
      saveOpenState();
      isSearching = true;
    }

    // Phase 1: hide all items
    allItems.forEach(function (item) {
      item.classList.add("org-tree__item--hidden");
    });

    // Phase 2: find matches and reveal them + ancestors
    var hasMatch = false;
    allItems.forEach(function (item) {
      if (item.classList.contains("org-tree__item--group")) return; // groups shown via ancestors
      if (matches(item, query)) {
        hasMatch = true;
        item.classList.remove("org-tree__item--hidden");
        showAncestors(item);
        showDescendants(item);
      }
    });

    // Phase 3: highlight matching text in visible labels
    root.querySelectorAll("mark").forEach(function (m) {
      var parent = m.parentNode;
      parent.replaceChild(document.createTextNode(m.textContent), m);
      parent.normalize();
    });
    root
      .querySelectorAll(
        ".org-tree__item:not(.org-tree__item--hidden) .org-tree__label",
      )
      .forEach(function (label) {
        highlightText(label, query);
      });

    // Phase 4: show/hide empty message
    if (hasMatch) {
      emptyMsg.style.display = "none";
      root.style.display = "";
    } else {
      emptyMsg.style.display = "";
      root.style.display = "none";
    }
  }

  function highlightText(el, query) {
    var text = el.textContent;
    var lower = text.toLowerCase();
    var idx = lower.indexOf(query);
    if (idx === -1) return;

    var frag = document.createDocumentFragment();
    var lastIdx = 0;
    while (idx !== -1) {
      if (idx > lastIdx) {
        frag.appendChild(document.createTextNode(text.slice(lastIdx, idx)));
      }
      var mark = document.createElement("mark");
      mark.textContent = text.slice(idx, idx + query.length);
      frag.appendChild(mark);
      lastIdx = idx + query.length;
      idx = lower.indexOf(query, lastIdx);
    }
    if (lastIdx < text.length) {
      frag.appendChild(document.createTextNode(text.slice(lastIdx)));
    }
    el.textContent = "";
    el.appendChild(frag);
  }

  // Debounced input handler
  var timer = null;
  input.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var query = input.value.toLowerCase().trim();
      filterTree(query);
    }, 150);
  });
})();
