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
  var CHEVRON_ICON = "20";
  // A group row's chevron is a bare cell, not a segment, so nothing separates it
  // from the label. Same gap as the org-beheer tree (organization_admin.html),
  // which pairs a bare chevron cell with its text the same way.
  var GROUP_CHEVRON_GAP = "12";
  var INDENT_STEP = "16";
  // Below this, a query matches so many orgs it would force-build most of the
  // tree — the very cost lazy rendering exists to avoid. See `filter`.
  var MIN_SEARCH_LENGTH = 2;

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

  OrgTree.prototype.render = function () {
    // Branches start collapsed simply by not carrying `expanded`.
    var list = cell("nldd-list", {
      type: "tree",
      variant: "simple",
      dividers: "never",
      "accessible-label": this.accessibleLabel,
    });
    // Build ONLY the root rows up front (a handful of org-type groups). Every
    // branch — including a group's immediate children — is materialised the
    // first time it is expanded (see `_ensureChildren`). At production scale the
    // groups' direct children alone were ~2.6k rows / ~21k DS web components:
    // ~0.2s to build, and the resulting huge connected Lit tree made every later
    // interaction (sync/filter/keyboard) sluggish. Starting fully collapsed keeps
    // the live DOM tiny (~25 rows) until the user opens a branch.
    for (var i = 0; i < this.state.roots.length; i++) {
      list.appendChild(this._buildRow(this.state.roots[i], 0));
    }
    this.container.appendChild(list);
    this._bindKeyboard();
    return this;
  };

  /**
   * Build the direct child rows of `node` if they aren't built yet, appending
   * them into the node's already-built row. Grandchildren are left for their
   * own parents to build lazily. Idempotent: safe to call on every expand.
   */
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
      // Build this branch's children the first time it opens, not on modal
      // load. `expanded` only reveals rows that already exist in the slot.
      if (willExpand) self._ensureChildren(node);
      row.toggleAttribute("expanded", willExpand);
    }

    var label = node.self ? 'Direct onder "' + node.label + '"' : node.label;
    var selectable = this.isSelectable(node);
    // A group row carries no checkbox, so expanding is its only action and the
    // ROW is the control: whole row clickable, chevron cell marked `disclosure`
    // so it still turns. A segmented action is for rows with more than one
    // action — here that is a selectable branch, where the chevron expands and
    // the label toggles the checkbox.
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
        // Child rows sit INSIDE this row (slot="children"), so their clicks
        // bubble through it. Without this guard, ticking a child collapses its
        // group. Only this row's own control toggles it.
        if (rowOf(e.composedPath()) !== row) return;
        toggleExpanded();
      });
    } else if (hasChildren) {
      // `disclosure` makes the chevron announce the ROW's expanded state, so the
      // open/closed state lives in one place and drives the group as well.
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

    // The row itself is the control for a group row, so its cells go straight
    // in the row — nesting them in an action would put a control in a control.
    var action = rowIsControl
      ? row
      : cell("nldd-list-item-action", {
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

    // A branch can be built long after selections were restored or a parent was
    // checked, so mirror the node's current state onto the fresh row now.
    if (selectable) this._syncRow(node, row);

    // Children are built lazily by `_ensureChildren`, not here — see `render`.
    return row;
  };

  /* We mark the rows the user picked HERSELF with data-explicit and style those
     apart (bold label, darker checkbox). The checkbox `checked` state alone can't
     tell them from rows that only turned on because all their children did — both
     are simply checked — and the footer tokens are easy to miss, so the tree
     needs its own cue for which row IS the selection. Not the DS `selected`
     attribute: it resolves to the same tokens as `checked`, so it would look
     identical. See app.css for the [data-explicit] styling. */
  /** Mirror one node's selection state onto its row. Rows that aren't built yet
   *  (lazy branches) pick this up in `_buildRow` when they are created. */
  OrgTree.prototype._syncRow = function (node, row) {
    var action = row.querySelector(":scope > nldd-list-item-action[checkbox]");
    if (action) action.checked = node.checked;
    var box = row.querySelector(
      ":scope > nldd-list-item-action[checkbox] nldd-checkbox",
    );
    if (box) {
      box.checked = node.checked;
      box.indeterminate = node.indeterminate;
    }
    row.toggleAttribute(
      "data-explicit",
      this.state.explicitSelections.has(node.id),
    );
  };

  OrgTree.prototype.sync = function () {
    var self = this;
    this.state.nodes.forEach(function (node) {
      var row = self.domNodes.get(node.id);
      if (row) self._syncRow(node, row);
    });
  };

  /** Opens every branch above a node, so a restored selection is in view.
   *  The node may sit inside a branch that was never expanded, so its row (and
   *  its ancestors' child rows) might not be built yet. Walk the model's
   *  ancestor chain top-down, building each level, before setting `expanded`. */
  OrgTree.prototype.expandAncestorsOf = function (nodeId) {
    var node = this.state.getNode(nodeId);
    if (!node) return;
    // Collect ancestors from the root down to (but excluding) the node itself.
    var chain = [];
    var ancestor = node.parent;
    while (ancestor) {
      chain.unshift(ancestor);
      ancestor = ancestor.parent;
    }
    for (var i = 0; i < chain.length; i++) {
      this._ensureChildren(chain[i]); // builds the next level down
      var row = this.domNodes.get(chain[i].id);
      if (row) row.setAttribute("expanded", "");
    }
  };

  OrgTree.prototype.filter = function (query) {
    var self = this;
    var q = query.toLowerCase().trim();

    // A one-character query matches nearly every org, which would force-build
    // almost the whole tree and re-introduce the open-time hang. Treat queries
    // shorter than two characters as empty: reveal nothing new, restore state.
    if (q.length < MIN_SEARCH_LENGTH) q = "";

    if (!q) {
      // Restore the pre-search expansion instead of collapsing everything, so
      // branches opened for a restored selection stay in view.
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

    // Snapshot the expansion once, at the start of a search, to restore on clear.
    if (!this.savedExpanded) {
      this.savedExpanded = new Map();
      this.domNodes.forEach(function (row) {
        self.savedExpanded.set(row, row.hasAttribute("expanded"));
      });
    }

    // A match may live inside a branch that was never expanded, so its row
    // isn't built. Build the path down to every match first, then hide-all and
    // reveal, so the reveal pass sees a complete DOM for the matching subtrees.
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

  // Keyboard nav follows the WAI-ARIA Treeview pattern (↑/↓ visible nodes,
  // ←/→ collapse/expand, Home/End first/last; Space toggles via the segment).

  OrgTree.prototype._visibleRows = function () {
    return Array.from(this.container.querySelectorAll("nldd-list-item")).filter(
      function (row) {
        if (row.hidden) return false;
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

  /** The checkbox segment carries the row; a group row IS the control, so it
   *  takes focus itself. Either way every row in the tree is reachable. */
  function focusRow(row) {
    var action =
      row.querySelector(":scope > nldd-list-item-action[checkbox]") ||
      row.querySelector(":scope > nldd-list-item-action");
    if (action && action.focus) action.focus();
    else if (row.focus) row.focus();
  }

  function hasBranch(row) {
    return (
      row.querySelector(':scope > nldd-list-item[slot="children"]') !== null
    );
  }

  /** The row a key event came from. Walks the composed path rather than using
   *  closest(): the focused control is a `<button>` inside a shadow root, either
   *  the segmented action's or — on a group row — the row's own, and closest()
   *  stops at that boundary. The first row in the path is the innermost one. */
  function rowOf(path) {
    for (var i = 0; i < path.length; i++) {
      var el = path[i];
      if (el.tagName && el.tagName.toLowerCase() === "nldd-list-item") {
        return el;
      }
    }
    return null;
  }

  OrgTree.prototype._bindKeyboard = function () {
    var self = this;
    this.container.addEventListener("keydown", function (e) {
      var li = rowOf(e.composedPath());
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
          // Branch-ness comes from the model, not built DOM: a collapsed lazy
          // branch has a chevron but no child rows yet. Build them on expand.
          var node = self.state.getNode(li.dataset.nodeId);
          if (node && node.children.length > 0) {
            if (!li.hasAttribute("expanded")) {
              self._ensureChildren(node);
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
