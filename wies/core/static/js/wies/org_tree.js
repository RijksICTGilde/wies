"use strict";

/**
 * Shared organisation-tree UI, built on DS components.
 *
 * Two pickers use the same tree: the opdrachtgever filter sheet (client_tree.js)
 * and the org picker on the assignment form (assignment_org_tree.js). Only the
 * footer differs — what a selection means and what it is applied to — so this
 * module owns the tree and nothing else: no tokens, no apply button, no inputs.
 *
 * A row is an nldd-list-item; child rows go in its slot="children", which the
 * component renders as role="group". Level, position and set size come out of
 * that nesting, so none of them are written here. Indentation is ours: one
 * spacer-cell per level, because nesting is structure and indenting is looks.
 *
 * Selection state lives in the TreeState passed in; this module only mirrors it
 * onto the DOM (sync) and reports toggles back (onToggle).
 */
(function () {
  // Segments stay in the grid, so the chevron zone is simply one control
  // width (44) on every row; a leaf row's stand-in spacer matches it, at any
  // depth.
  var LEAF_CHEVRON_ZONE = "44";
  var INDENT_STEP = "16";

  function cell(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      el.setAttribute(k, attrs[k]);
    });
    return el;
  }

  /**
   * @param {object} options
   * @param {TreeState} options.state      Selection state (owned by the caller).
   * @param {Element}   options.container  Element the tree is rendered into.
   * @param {boolean}  [options.showCounts=true]   Render the placement count per row.
   * @param {function} [options.isSelectable]      Node → whether the row gets a checkbox.
   * @param {function} [options.onToggle]          (node, checked) after a row toggles.
   * @param {string}   [options.accessibleLabel]
   */
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

  // ============================================================
  // BUILD
  // ============================================================

  OrgTree.prototype.render = function () {
    // nldd-list type="tree" gives role="tree"; the rows become treeitem and their
    // slot="children" the role="group". Branches start collapsed simply by not
    // carrying `expanded`.
    var list = cell("nldd-list", {
      type: "tree",
      variant: "simple",
      "no-dividers": "",
      "accessible-label": this.accessibleLabel,
    });
    for (var i = 0; i < this.state.roots.length; i++) {
      list.appendChild(this._buildRow(this.state.roots[i], 0));
    }
    this.container.appendChild(list);
    this._bindKeyboard();
    return this;
  };

  OrgTree.prototype._buildRow = function (node, depth) {
    var self = this;
    var hasChildren = node.children.length > 0;
    var row = cell("nldd-list-item", {});
    row.dataset.nodeId = node.id;
    if (depth) row.setAttribute("slot", "children");
    this.domNodes.set(node.id, row);

    for (var d = 0; d < depth; d++) {
      row.appendChild(cell("nldd-spacer-cell", { size: INDENT_STEP }));
    }

    if (hasChildren) {
      // `disclosure` makes the chevron announce the ROW's expanded state, so the
      // open/closed state lives in one place and drives the group as well.
      var chevron = cell("nldd-list-item-action", {
        button: "",
        disclosure: "",
        "accessible-label": node.label + " in- of uitklappen",
      });
      var iconCell = cell("nldd-icon-cell", { size: "20" });
      iconCell.appendChild(cell("nldd-icon", { name: "chevron-right" }));
      chevron.appendChild(iconCell);
      chevron.addEventListener("click", function () {
        row.toggleAttribute("expanded", !row.hasAttribute("expanded"));
      });
      row.appendChild(chevron);
    } else {
      // Matches the chevron's in-grid width, or leaf rows drift.
      row.appendChild(cell("nldd-spacer-cell", { size: LEAF_CHEVRON_ZONE }));
    }

    var label = node.self ? 'Direct onder "' + node.label + '"' : node.label;
    var selectable = this.isSelectable(node);
    var action = cell("nldd-list-item-action", {
      width: "full",
      "accessible-label": label,
    });
    if (selectable) action.setAttribute("checkbox", "");
    if (selectable) {
      var boxCell = cell("nldd-cell", {});
      // Decorative: the row segment already carries role and state, and a second
      // focusable control would double the tab stops.
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
      action.addEventListener("change", function (e) {
        var checked = !!(e.detail && e.detail.checked);
        if (checked) {
          self.state.check(node.id);
          // Expanding on check keeps what you just selected in view.
          if (hasChildren) row.setAttribute("expanded", "");
        } else {
          self.state.uncheck(node.id);
        }
        self.sync();
        self.onToggle(node, checked);
      });
    }
    row.appendChild(action);

    for (var i = 0; i < node.children.length; i++) {
      row.appendChild(this._buildRow(node.children[i], depth + 1));
    }

    return row;
  };

  // ============================================================
  // SYNC — read state, write DOM
  // ============================================================

  /* Deliberately no `selected` on the row. The checkbox segment already paints
     its own checked fill, and a row-level one bleeds out past the chevron — so a
     row you picked yourself would look different from one that turned on because
     all its children did, while both are simply checked. Which of the two is the
     explicit choice is what the footer says. */
  OrgTree.prototype.sync = function () {
    var self = this;
    this.state.nodes.forEach(function (node) {
      var row = self.domNodes.get(node.id);
      if (!row) return;
      var action = row.querySelector(
        ":scope > nldd-list-item-action[checkbox]",
      );
      if (action) action.checked = node.checked;
      var box = row.querySelector(
        ":scope > nldd-list-item-action[checkbox] nldd-checkbox",
      );
      if (box) {
        box.checked = node.checked;
        box.indeterminate = node.indeterminate;
      }
    });
  };

  /** Opens every branch above a node, so a restored selection is in view. */
  OrgTree.prototype.expandAncestorsOf = function (nodeId) {
    var row = this.domNodes.get(String(nodeId));
    var ancestor =
      row && row.parentElement && row.parentElement.closest("nldd-list-item");
    while (ancestor) {
      ancestor.setAttribute("expanded", "");
      ancestor =
        ancestor.parentElement &&
        ancestor.parentElement.closest("nldd-list-item");
    }
  };

  // ============================================================
  // SEARCH
  // ============================================================

  OrgTree.prototype.filter = function (query) {
    var self = this;
    var q = query.toLowerCase().trim();

    if (!q) {
      this.domNodes.forEach(function (row) {
        row.hidden = false;
        row.removeAttribute("expanded");
      });
      return;
    }

    // While searching, every branch is open: the hidden attribute alone decides
    // what you see, so a collapsed ancestor can never swallow a match.
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

  // ============================================================
  // KEYBOARD NAVIGATION (WAI-ARIA Treeview pattern)
  // ↑/↓ = navigate visible nodes, ←/→ = collapse/expand,
  // Home/End = first/last node. Space toggles via the focused segment.
  // ============================================================

  OrgTree.prototype._visibleRows = function () {
    return Array.from(this.container.querySelectorAll("nldd-list-item")).filter(
      function (row) {
        if (row.hidden) return false;
        // Visible only if every ancestor branch is expanded.
        var parent =
          row.parentElement && row.parentElement.closest("nldd-list-item");
        while (parent) {
          if (!parent.hasAttribute("expanded")) return false;
          parent =
            parent.parentElement &&
            parent.parentElement.closest("nldd-list-item");
        }
        return true;
      },
    );
  };

  /** The checkbox segment carries the row; a group row without one falls back to
   *  its chevron, so every row in the tree is reachable. */
  function focusRow(row) {
    var action =
      row.querySelector(":scope > nldd-list-item-action[checkbox]") ||
      row.querySelector(":scope > nldd-list-item-action");
    if (action && action.focus) action.focus();
  }

  function hasBranch(row) {
    return (
      row.querySelector(':scope > nldd-list-item[slot="children"]') !== null
    );
  }

  function rowOf(el) {
    var action = el.closest && el.closest("nldd-list-item-action");
    return action ? action.closest("nldd-list-item") : null;
  }

  OrgTree.prototype._bindKeyboard = function () {
    var self = this;
    this.container.addEventListener("keydown", function (e) {
      var li = rowOf(e.composedPath()[0]);
      if (!li) return;

      var visible = self._visibleRows();
      var idx = visible.indexOf(li);

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          if (idx < visible.length - 1) focusRow(visible[idx + 1]);
          break;
        case "ArrowUp":
          e.preventDefault();
          if (idx > 0) focusRow(visible[idx - 1]);
          break;
        case "ArrowRight":
          e.preventDefault();
          if (hasBranch(li)) {
            if (!li.hasAttribute("expanded")) {
              li.setAttribute("expanded", "");
            } else {
              var firstChild = li.querySelector(
                ':scope > nldd-list-item[slot="children"]:not([hidden])',
              );
              if (firstChild) focusRow(firstChild);
            }
          }
          break;
        case "ArrowLeft":
          e.preventDefault();
          if (hasBranch(li) && li.hasAttribute("expanded")) {
            li.removeAttribute("expanded");
          } else {
            var parentLi =
              li.parentElement && li.parentElement.closest("nldd-list-item");
            if (parentLi) focusRow(parentLi);
          }
          break;
        case "Home":
          e.preventDefault();
          if (visible.length > 0) focusRow(visible[0]);
          break;
        case "End":
          e.preventDefault();
          if (visible.length > 0) focusRow(visible[visible.length - 1]);
          break;
      }
    });
  };

  /** Debounced search wiring, identical in both pickers. */
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
