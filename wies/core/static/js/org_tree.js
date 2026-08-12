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

  /** The row's visible label. A `self` node stands for "the organisation
   *  itself", next to its own children. */
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

    var label = rowLabel(node);
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
    // A selectable row's segment is a `button` action, NOT a `checkbox` action:
    // a checkbox action paints the row-wide grey "selected" fill on every checked
    // row via its internal .is-action-checked — including a child that only
    // cascaded on because its parent was picked — and that fill can't be
    // suppressed per-attribute. A button action doesn't paint it, so the grey
    // comes solely from the DS `selected` attribute, set only on the row the user
    // picked herself (see _syncRow). The button is still one control / one tab
    // stop and gives the row its hover and focus state.
    var action = rowIsControl
      ? row
      : cell("nldd-list-item-action", {
          width: "full",
          "accessible-label": label,
        });
    if (selectable) {
      action.setAttribute("button", "");
      var boxCell = cell("nldd-cell", {});
      // Decorative: the button segment carries role and state (promoted to a
      // checkbox for assistive tech in _syncRow), and a second focusable control
      // would double the tab stops.
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
      // A `button` action doesn't toggle anything itself — it just fires a click
      // (from a mouse press or Space/Enter on the button). We own the checked
      // state in TreeState, so read the node's current state and flip it. Guard
      // against a child row's click bubbling up: the action segment is a sibling
      // of the child rows, but the click listener sits on the row-level action,
      // so only presses on this row's own button count.
      action.addEventListener("click", function (e) {
        if (rowOf(e.composedPath()) !== row) return;
        // Toggle off the visible tick, on otherwise. A parent showing a dash
        // (indeterminate: some children on) is not "ticked", so a click selects
        // the whole subtree rather than clearing it.
        var checked = !(node.checked && !node.indeterminate);
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

  /** Mirror one node's selection state onto its row. Rows that aren't built yet
   *  (lazy branches) pick this up in `_buildRow` when they are created.
   *
   *  The tree needs its own cue for which row IS the selection: a parent lights
   *  up (checkbox checked) both when the user picked it herself and when it only
   *  cascaded on because all its children are on, and the footer tokens are easy
   *  to miss. The cue is the row-wide grey fill via the DS `selected` attribute,
   *  set ONLY on a row the user picked herself (in explicitSelections). Because
   *  the segment is a `button` action (not a `checkbox` action), a checked
   *  checkbox no longer paints that fill itself, so `selected` is the sole source
   *  of grey — a cascaded child stays checked but ungreyed. No DS variable is
   *  overridden.
   *
   *  The visible checkbox is decorative; the button carries the state for
   *  assistive tech. A `button` action renders a bare <button>, so promote it to
   *  role="checkbox" and keep aria-checked in step here. Lit owns neither
   *  attribute on a button control, so they survive its re-renders. */
  OrgTree.prototype._syncRow = function (node, row) {
    // The selection button, not the chevron: a selectable branch has both, and
    // the chevron is the `disclosure` one.
    var action = row.querySelector(
      ":scope > nldd-list-item-action[button]:not([disclosure])",
    );
    var box = action && action.querySelector("nldd-checkbox");
    if (box) {
      box.checked = node.checked;
      box.indeterminate = node.indeterminate;
    }
    // A dash (indeterminate) reads as "mixed"; otherwise the tick's state.
    var ariaChecked = node.indeterminate ? "mixed" : String(node.checked);
    if (action) promoteButtonToCheckbox(action, ariaChecked);
    row.toggleAttribute("selected", this.state.explicitSelections.has(node.id));
  };

  /** Give a `button` action the checkbox role and state for assistive tech. The
   *  inner <button> may not exist yet on the first sync (Lit renders it a tick
   *  after the action is created), so wait on updateComplete when it's missing.
   *  Lit owns neither attribute on a button control, so they survive re-renders. */
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

  // nldd-list[type=tree] handles the WAI-ARIA treeview keys itself. Only
  // ArrowRight needs us: it opens what is already built, and a collapsed lazy
  // branch has a chevron but no child rows yet.
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
