/**
 * Shared organization tree picker logic.
 *
 * Usage:
 *   new OrgTreePicker({
 *     dataElementId: "...",
 *     containerId: "...",
 *     selectionListId: "...",
 *     searchInputId: "...",
 *     clearBtnId: "...",
 *     applyBtnId: "...",
 *     countElementId: "...",          // optional
 *     currentSelectionsId: "...",
 *     checkboxIdPrefix: "...",
 *     skipGroupCheckboxes: false,     // true = group nodes are not checkable
 *     showBadges: false,              // true = show nr_of_placements badge
 *     expandOnCheck: false,           // true = expand parent on check
 *     onApply: function(treeState) {},
 *     onClear: function(treeState) {},
 *     onSync: function(treeState) {}, // called after every sync
 *   });
 */
(function () {
  "use strict";

  function OrgTreePicker(config) {
    var dataEl = document.getElementById(config.dataElementId);
    var data = dataEl ? JSON.parse(dataEl.textContent) : [];
    this.container = document.getElementById(config.containerId);
    this.selectionList = document.getElementById(config.selectionListId);
    this.searchInput = document.getElementById(config.searchInputId);
    this.clearBtn = document.getElementById(config.clearBtnId);
    this.applyBtn = document.getElementById(config.applyBtnId);
    this.countElementId = config.countElementId;
    this.checkboxIdPrefix = config.checkboxIdPrefix || "tree-node-";
    this.skipGroupCheckboxes = !!config.skipGroupCheckboxes;
    this.showBadges = !!config.showBadges;
    this.expandOnCheck = !!config.expandOnCheck;
    this.onApply = config.onApply || function () {};
    this.onClear = config.onClear || function () {};
    this.onSync = config.onSync || function () {};

    if (!this.container) return;

    this.treeState = new TreeState(data);
    this.domNodes = new Map();

    this._renderTree(data);
    this._bindEvents();
    this._restoreSelections(config.currentSelectionsId);
  }

  // ============================================================
  // TREE BUILDING
  // ============================================================

  OrgTreePicker.prototype._buildTree = function (node) {
    var self = this;
    var li = document.createElement("li");
    li.className =
      "client-tree-node" +
      (node.children && node.children.length ? " has-children" : "") +
      (node.self ? " self-node" : "");
    li.dataset.nodeId = String(node.id);
    self.domNodes.set(String(node.id), li);

    if (node.children && node.children.length) {
      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "client-toggle";
      toggle.textContent = "\u203A";
      toggle.title = "Uitklappen/inklappen";
      toggle.setAttribute("aria-label", "Uitklappen/inklappen");
      toggle.addEventListener("click", function () {
        li.classList.toggle("collapsed");
      });
      li.appendChild(toggle);
    } else {
      var spacer = document.createElement("span");
      spacer.className = "client-toggle-spacer";
      li.appendChild(spacer);
    }

    var isGroup = String(node.id).startsWith("group-");
    var checkboxId = self.checkboxIdPrefix + String(node.id);
    var label = document.createElement("label");
    label.htmlFor = checkboxId;

    if (self.skipGroupCheckboxes && isGroup) {
      label.style.cursor = "pointer";
      label.addEventListener("click", function (e) {
        e.preventDefault();
        li.classList.toggle("collapsed");
      });
    } else {
      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = checkboxId;
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) {
          self.treeState.check(node.id);
        } else {
          self.treeState.uncheck(node.id);
        }
        self._syncAllDOM();
        if (
          self.expandOnCheck &&
          checkbox.checked &&
          li.classList.contains("has-children")
        ) {
          li.classList.remove("collapsed");
        }
      });
      label.appendChild(checkbox);
    }

    var displayText = node.self
      ? 'Direct onder "' + node.label + '"'
      : node.label;
    label.appendChild(document.createTextNode(displayText));

    if (self.showBadges && node.nr_of_placements !== undefined) {
      var badge = document.createElement("span");
      badge.className = "client-placement-badge";
      badge.textContent = node.nr_of_placements;
      label.appendChild(badge);
    }

    li.appendChild(label);

    if (node.children && node.children.length) {
      var childUl = document.createElement("ul");
      childUl.className = "client-tree-level";
      for (var i = 0; i < node.children.length; i++) {
        childUl.appendChild(self._buildTree(node.children[i]));
      }
      li.appendChild(childUl);
    }

    return li;
  };

  // ============================================================
  // DOM SYNC
  // ============================================================

  OrgTreePicker.prototype._syncAllDOM = function () {
    var self = this;
    self.treeState.nodes.forEach(function (node) {
      var li = self.domNodes.get(node.id);
      if (!li) return;
      var cb = li.querySelector(":scope > label > input[type='checkbox']");
      if (cb) {
        cb.checked = node.checked;
        cb.indeterminate = node.indeterminate;
      }
    });
    self._updateHighlightClasses();
    self._rebuildSelectionList();
    self.onSync(self.treeState);
  };

  OrgTreePicker.prototype._updateHighlightClasses = function () {
    var self = this;
    self.domNodes.forEach(function (li, nodeId) {
      li.classList.toggle(
        "checked",
        self.treeState.explicitSelections.has(nodeId),
      );
    });
  };

  // ============================================================
  // SELECTION PANEL
  // ============================================================

  OrgTreePicker.prototype._rebuildSelectionList = function () {
    var self = this;
    self.selectionList.innerHTML = "";

    if (self.countElementId) {
      var countEl = document.getElementById(self.countElementId);
      if (countEl) {
        var count = self.treeState.explicitSelections.size;
        countEl.textContent = count;
        countEl.style.display = count > 0 ? "" : "none";
      }
    }

    if (self.treeState.explicitSelections.size === 0) return;

    for (var entry of self.treeState.explicitSelections) {
      var nodeId = entry[0];
      var text = entry[1];
      var li = document.createElement("li");
      li.className = "client-modal__selection-item";
      var span = document.createElement("span");
      span.textContent = text;
      span.title = text;
      li.appendChild(span);
      var removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "client-modal__selection-remove";
      removeBtn.setAttribute("aria-label", "Verwijder " + text);
      removeBtn.textContent = "\u00D7";
      removeBtn.addEventListener(
        "click",
        (function (id) {
          return function () {
            self.treeState.removeSelection(id);
            self._syncAllDOM();
          };
        })(nodeId),
      );
      li.appendChild(removeBtn);
      self.selectionList.appendChild(li);
    }
  };

  // ============================================================
  // SEARCH FILTERING
  // ============================================================

  OrgTreePicker.prototype._filterTree = function (query) {
    var self = this;
    var q = query.toLowerCase().trim();
    var allNodes = self.container.querySelectorAll("li.client-tree-node");

    if (!q) {
      allNodes.forEach(function (li) {
        li.classList.remove("search-hidden");
        li.classList.remove("search-match");
      });
      self.container
        .querySelectorAll("li.client-tree-node.has-children")
        .forEach(function (li) {
          li.classList.add("collapsed");
        });
      self.onSync(self.treeState);
      return;
    }

    var matchingNodes = new Set();
    self.treeState.nodes.forEach(function (node) {
      var matches = false;
      if (node.label && node.label.toLowerCase().includes(q)) matches = true;
      if (!matches && node.abbreviations) {
        for (var i = 0; i < node.abbreviations.length; i++) {
          if (node.abbreviations[i].toLowerCase().includes(q)) {
            matches = true;
            break;
          }
        }
      }
      if (matches) matchingNodes.add(node.id);
    });

    var visibleNodes = new Set(matchingNodes);
    matchingNodes.forEach(function (nodeId) {
      var node = self.treeState.nodes.get(nodeId);
      if (!node) return;
      var ancestor = node.parent;
      while (ancestor) {
        visibleNodes.add(ancestor.id);
        ancestor = ancestor.parent;
      }
    });

    allNodes.forEach(function (li) {
      var nodeId = li.dataset.nodeId;
      if (visibleNodes.has(nodeId)) {
        li.classList.remove("search-hidden");
        li.classList.remove("collapsed");
        li.classList.toggle("search-match", matchingNodes.has(nodeId));
      } else {
        li.classList.add("search-hidden");
        li.classList.remove("search-match");
        li.classList.remove("collapsed");
      }
    });
    self.onSync(self.treeState);
  };

  // ============================================================
  // RENDER & EVENTS
  // ============================================================

  OrgTreePicker.prototype._renderTree = function (data) {
    var self = this;
    self.container.innerHTML = "";
    var rootUl = document.createElement("ul");
    rootUl.className = "client-tree-level";
    for (var i = 0; i < data.length; i++) {
      rootUl.appendChild(self._buildTree(data[i]));
    }
    self.container.appendChild(rootUl);

    self.container
      .querySelectorAll("li.client-tree-node.has-children")
      .forEach(function (li) {
        li.classList.add("collapsed");
      });
  };

  OrgTreePicker.prototype._bindEvents = function () {
    var self = this;

    if (self.searchInput) {
      var debounceTimer;
      self.searchInput.addEventListener("input", function () {
        var value = this.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
          self._filterTree(value);
        }, 300);
      });
    }

    if (self.clearBtn) {
      self.clearBtn.addEventListener("click", function () {
        self.treeState.clearAll();
        self._syncAllDOM();
        self.onClear(self.treeState);
      });
    }

    if (self.applyBtn) {
      self.applyBtn.addEventListener("click", function () {
        self.onApply(self.treeState);
      });
    }
  };

  OrgTreePicker.prototype._restoreSelections = function (selectionsElId) {
    var self = this;
    var selectionsEl = document.getElementById(selectionsElId);
    var currentSelections = selectionsEl
      ? JSON.parse(selectionsEl.textContent)
      : {};
    if (Object.keys(currentSelections).length > 0) {
      self.treeState.restoreSelections(currentSelections);
      self._syncAllDOM();
      for (var nodeId in currentSelections) {
        var li = self.domNodes.get(nodeId);
        if (li) {
          var ancestor = li.parentElement && li.parentElement.parentElement;
          while (ancestor && ancestor.classList.contains("client-tree-node")) {
            ancestor.classList.remove("collapsed");
            ancestor =
              ancestor.parentElement && ancestor.parentElement.parentElement;
          }
        }
      }
    }
  };

  window.OrgTreePicker = OrgTreePicker;
})();
