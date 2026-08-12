"use strict";

/**
 * Shared organisation-tree UI for the filter sheet (client_tree.js) and the
 * assignment form's org picker (assignment_org_tree.js). Owns the tree only.
 */
(function () {
  var LEAF_CHEVRON_ZONE = "44";
  var CHEVRON_ICON = "20";
  var GROUP_CHEVRON_GAP = "12";
  var INDENT_STEP = "16";
  // Shorter queries match nearly every org and would force-build the tree.
  var MIN_SEARCH_LENGTH = 2;

  function rowLabel(node) {
    return node.self ? 'Direct onder "' + node.label + '"' : node.label;
  }

  function cell(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      el.setAttribute(k, attrs[k]);
    });
    return el;
  }

  /** options: state, container, showCounts, isSelectable, onToggle,
   *  accessibleLabel. */
  function OrgTree(options) {
    this.state = options.state;
    this.container = options.container;
    this.showCounts = options.showCounts !== false;
    this.isSelectable =
      options.isSelectable ||
      function () {
        return true;
      };
    this.onToggle = options.onToggle || function () {};
    this.accessibleLabel = options.accessibleLabel || "Organisaties";
    this.domNodes = new Map();
  }

  OrgTree.prototype.render = function () {
    var list = cell("nldd-list", {
      type: "tree",
      variant: "simple",
      dividers: "never",
      "accessible-label": this.accessibleLabel,
    });
    // Roots only: building eagerly was ~21k DS components and made every later
    // interaction sluggish.
    for (var i = 0; i < this.state.roots.length; i++) {
      list.appendChild(this._buildRow(this.state.roots[i], 0));
    }
    this.container.appendChild(list);
    this._bindKeyboard();
    return this;
  };

  OrgTree.prototype._ensureChildren = function (node) {
    var row = this.domNodes.get(node.id);
    if (!row || row.dataset.childrenBuilt) return;
    row.dataset.childrenBuilt = "1";
    var depth = Number(row.dataset.depth) + 1;
    for (var i = 0; i < node.children.length; i++) {
      row.appendChild(this._buildRow(node.children[i], depth));
    }
  };

  OrgTree.prototype._buildRow = function (node, depth) {
    var self = this;
    var hasChildren = node.children.length > 0;
    var row = cell("nldd-list-item", {});
    row.dataset.nodeId = node.id;
    row.dataset.depth = depth;
    if (depth) row.setAttribute("slot", "children");
    this.domNodes.set(node.id, row);

    for (var d = 0; d < depth; d++) {
      row.appendChild(cell("nldd-spacer-cell", { size: INDENT_STEP }));
    }

    function toggleExpanded() {
      var willExpand = !row.hasAttribute("expanded");
      // `expanded` only reveals rows that already exist in the slot.
      if (willExpand) self._ensureChildren(node);
      row.toggleAttribute("expanded", willExpand);
    }

    var label = rowLabel(node);
    var selectable = this.isSelectable(node);
    var rowIsControl = hasChildren && !selectable;

    if (rowIsControl) {
      row.setAttribute("button", "");
      var groupChevron = cell("nldd-icon-cell", {
        size: CHEVRON_ICON,
        disclosure: "",
      });
      groupChevron.appendChild(cell("nldd-icon", { name: "chevron-right" }));
      row.appendChild(groupChevron);
      row.appendChild(cell("nldd-spacer-cell", { size: GROUP_CHEVRON_GAP }));
      row.addEventListener("click", function (e) {
        // Child rows sit inside this row, so their clicks bubble through it.
        if (rowOf(e.composedPath()) !== row) return;
        toggleExpanded();
      });
    } else if (hasChildren) {
      // `disclosure` makes the chevron announce the ROW's expanded state.
      var chevron = cell("nldd-list-item-action", {
        button: "",
        disclosure: "",
        "accessible-label": node.label + " in- of uitklappen",
      });
      var iconCell = cell("nldd-icon-cell", { size: CHEVRON_ICON });
      iconCell.appendChild(cell("nldd-icon", { name: "chevron-right" }));
      chevron.appendChild(iconCell);
      chevron.addEventListener("click", toggleExpanded);
      row.appendChild(chevron);
    } else {
      // Matches the chevron's in-grid width, or leaf rows drift.
      row.appendChild(cell("nldd-spacer-cell", { size: LEAF_CHEVRON_ZONE }));
    }

    // A `button` action, not a `checkbox` action: the latter paints an
    // unsuppressable grey fill on every checked row, cascaded children included.
    var action = rowIsControl
      ? row
      : cell("nldd-list-item-action", {
          width: "full",
          "accessible-label": label,
        });
    if (selectable) {
      action.setAttribute("button", "");
      var boxCell = cell("nldd-cell", {});
      // Decorative: the button segment carries role and state (_syncRow).
      boxCell.appendChild(
        cell("nldd-checkbox", { "aria-hidden": "true", tabindex: "-1" }),
      );
      action.appendChild(boxCell);
      action.appendChild(cell("nldd-spacer-cell", { size: "8" }));
    }
    action.appendChild(cell("nldd-text-cell", { text: label }));
    if (this.showCounts && node.nr_of_placements !== undefined) {
      action.appendChild(cell("nldd-spacer-cell", { size: "8" }));
      action.appendChild(
        cell("nldd-text-cell", {
          text: String(node.nr_of_placements),
          width: "fit-content",
          "horizontal-alignment": "right",
          color: "secondary",
        }),
      );
    }
    if (selectable) {
      action.addEventListener("click", function (e) {
        if (rowOf(e.composedPath()) !== row) return;
        // A parent showing a dash is not "ticked", so a click selects the whole
        // subtree rather than clearing it.
        var checked = !(node.checked && !node.indeterminate);
        if (checked) {
          self.state.check(node.id);
          if (hasChildren) {
            self._ensureChildren(node);
            row.setAttribute("expanded", "");
          }
        } else {
          self.state.uncheck(node.id);
        }
        self.sync();
        self.onToggle(node, checked);
      });
    }
    if (action !== row) row.appendChild(action);

    // A branch can be built long after selections were restored.
    if (selectable) this._syncRow(node, row);

    return row;
  };

  // `selected` (the grey fill) marks only what the user picked herself, so a
  // cascaded child stays checked but ungreyed.
  OrgTree.prototype._syncRow = function (node, row) {
    // The selection button, not the chevron (the `disclosure` one).
    var action = row.querySelector(
      ":scope > nldd-list-item-action[button]:not([disclosure])",
    );
    var box = action && action.querySelector("nldd-checkbox");
    if (box) {
      box.checked = node.checked;
      box.indeterminate = node.indeterminate;
    }
    var ariaChecked = node.indeterminate ? "mixed" : String(node.checked);
    if (action) promoteButtonToCheckbox(action, ariaChecked);
    row.toggleAttribute("selected", this.state.explicitSelections.has(node.id));
  };

  // The inner <button> may not exist on the first sync (Lit renders it a tick
  // later), hence the updateComplete fallback.
  function promoteButtonToCheckbox(action, ariaChecked) {
    var button = action.shadowRoot && action.shadowRoot.querySelector("button");
    if (button) {
      button.setAttribute("role", "checkbox");
      button.setAttribute("aria-checked", ariaChecked);
    } else if (action.updateComplete) {
      action.updateComplete.then(function () {
        var b = action.shadowRoot && action.shadowRoot.querySelector("button");
        if (b) {
          b.setAttribute("role", "checkbox");
          b.setAttribute("aria-checked", ariaChecked);
        }
      });
    }
  }

  OrgTree.prototype.sync = function () {
    var self = this;
    this.state.nodes.forEach(function (node) {
      var row = self.domNodes.get(node.id);
      if (row) self._syncRow(node, row);
    });
  };

  // Walks the model's ancestor chain top-down: those rows may not exist yet.
  OrgTree.prototype.expandAncestorsOf = function (nodeId) {
    var node = this.state.getNode(nodeId);
    if (!node) return;
    var chain = [];
    var ancestor = node.parent;
    while (ancestor) {
      chain.unshift(ancestor);
      ancestor = ancestor.parent;
    }
    for (var i = 0; i < chain.length; i++) {
      this._ensureChildren(chain[i]);
      var row = this.domNodes.get(chain[i].id);
      if (row) row.setAttribute("expanded", "");
    }
  };

  OrgTree.prototype.filter = function (query) {
    var self = this;
    var q = query.toLowerCase().trim();

    if (q.length < MIN_SEARCH_LENGTH) q = "";

    if (!q) {
      // Restore the pre-search expansion rather than collapsing everything.
      this.domNodes.forEach(function (row) {
        row.hidden = false;
        var wasExpanded = self.savedExpanded
          ? self.savedExpanded.get(row)
          : false;
        row.toggleAttribute("expanded", Boolean(wasExpanded));
      });
      this.savedExpanded = null;
      return;
    }

    if (!this.savedExpanded) {
      this.savedExpanded = new Map();
      this.domNodes.forEach(function (row) {
        self.savedExpanded.set(row, row.hasAttribute("expanded"));
      });
    }

    // Build the path to every match first, so the reveal pass below sees a
    // complete DOM.
    this.state.nodes.forEach(function (node) {
      if (!TreeState.nodeMatches(node, q)) return;
      var chain = [];
      var ancestor = node.parent;
      while (ancestor) {
        chain.unshift(ancestor);
        ancestor = ancestor.parent;
      }
      for (var i = 0; i < chain.length; i++) self._ensureChildren(chain[i]);
    });

    // Everything open while searching, so no collapsed ancestor swallows a
    // match: `hidden` alone decides what you see.
    this.domNodes.forEach(function (row) {
      row.hidden = true;
      row.setAttribute("expanded", "");
    });

    this.state.nodes.forEach(function (node) {
      if (!TreeState.nodeMatches(node, q)) return;
      var row = self.domNodes.get(node.id);
      if (row) row.hidden = false;
      var ancestor = node.parent;
      while (ancestor) {
        var ancestorRow = self.domNodes.get(ancestor.id);
        if (ancestorRow) ancestorRow.hidden = false;
        ancestor = ancestor.parent;
      }
    });
  };

  // Composed path rather than closest(): the focused control is a <button>
  // inside a shadow root, and closest() stops at that boundary.
  function rowOf(path) {
    for (var i = 0; i < path.length; i++) {
      var el = path[i];
      if (el.tagName && el.tagName.toLowerCase() === "nldd-list-item") {
        return el;
      }
    }
    return null;
  }

  // nldd-list[type=tree] handles the treeview keys itself, but ArrowRight only
  // opens what is already built, and a lazy branch has nothing yet.
  OrgTree.prototype._bindKeyboard = function () {
    var self = this;
    this.container.addEventListener(
      "keydown",
      function (e) {
        if (e.key !== "ArrowRight") return;
        var li = rowOf(e.composedPath());
        if (!li || li.hasAttribute("expanded")) return;
        var node = self.state.getNode(li.dataset.nodeId);
        if (node && node.children.length > 0) self._ensureChildren(node);
      },
      true,
    );
  };

  OrgTree.prototype.bindSearch = function (input, delay) {
    var self = this;
    if (!input) return this;
    var timer;
    input.addEventListener("input", function () {
      var value = this.value;
      clearTimeout(timer);
      timer = setTimeout(function () {
        self.filter(value);
      }, delay || 300);
    });
    return this;
  };

  window.WiesOrgTree = OrgTree;
})();
