"use strict";

/**
 * Checkbox cascading and selection tracking for a tree, DOM-free.
 *
 * `collapseToParent` (default true): a fully checked parent replaces its
 * children as the selection. Off on the assignment form, where a parent means
 * only itself and collapsing would drop the children the user picked.
 */
function TreeState(data, options) {
  this.nodes = new Map();
  this.roots = [];
  this.explicitSelections = new Map(); // nodeId → label
  this.collapseToParent = !options || options.collapseToParent !== false;

  this._buildIndex(data, null);
}

TreeState.prototype._buildIndex = function (nodes, parent) {
  for (var i = 0; i < nodes.length; i++) {
    var raw = nodes[i];
    var node = {
      id: String(raw.id),
      label: raw.label || "",
      abbreviations: raw.abbreviations || [],
      group: !!raw.group,
      self: !!raw.self,
      nr_of_placements: raw.nr_of_placements,
      checked: false,
      indeterminate: false,
      children: [],
      parent: parent,
    };
    this.nodes.set(node.id, node);
    if (parent) {
      parent.children.push(node);
    } else {
      this.roots.push(node);
    }
    if (raw.children) {
      this._buildIndex(raw.children, node);
    }
  }
};

TreeState.prototype.check = function (nodeId) {
  var node = this.nodes.get(String(nodeId));
  if (!node) return;
  node.checked = true;
  node.indeterminate = false;
  this._cascadeDown(node, true);
  this._cascadeUp(node);

  // Descendants are now implied by this selection.
  this.explicitSelections.set(node.id, this._getLabel(node));
  this._forEachDescendant(
    node,
    function (desc) {
      this.explicitSelections.delete(desc.id);
    }.bind(this),
  );
  this._promoteAncestors(node);
};

TreeState.prototype.uncheck = function (nodeId) {
  var node = this.nodes.get(String(nodeId));
  if (!node) return;
  node.checked = false;
  node.indeterminate = false;
  this._cascadeDown(node, false);
  this._cascadeUp(node);

  this.explicitSelections.delete(node.id);
  this._forEachDescendant(
    node,
    function (desc) {
      this.explicitSelections.delete(desc.id);
    }.bind(this),
  );
  this._demoteAncestors(node);
};

TreeState.prototype.removeSelection = function (nodeId) {
  var node = this.nodes.get(String(nodeId));
  if (!node) return;
  this.explicitSelections.delete(node.id);
  node.checked = false;
  node.indeterminate = false;
  this._cascadeDown(node, false);
  this._forEachDescendant(
    node,
    function (desc) {
      this.explicitSelections.delete(desc.id);
    }.bind(this),
  );
  this._cascadeUp(node);
};

TreeState.prototype.clearAll = function () {
  this.explicitSelections.clear();
  this.nodes.forEach(function (node) {
    node.checked = false;
    node.indeterminate = false;
  });
};

TreeState.prototype.restoreSelections = function (selections) {
  var entries = Object.entries(selections);
  for (var i = 0; i < entries.length; i++) {
    var nodeId = entries[i][0];
    var label = entries[i][1];
    var node = this.nodes.get(String(nodeId));
    if (node) {
      node.checked = true;
      node.indeterminate = false;
      this._cascadeDown(node, true);
      this._cascadeUp(node);
    }
    this.explicitSelections.set(String(nodeId), label);
  }

  // Same collapse as a hand-made selection, so both show the same tokens.
  var restored = Array.from(this.explicitSelections.keys());
  for (var j = 0; j < restored.length; j++) {
    var restoredNode = this.nodes.get(restored[j]);
    if (restoredNode) this._promoteAncestors(restoredNode);
  }
};

TreeState.prototype.getNode = function (nodeId) {
  return this.nodes.get(String(nodeId)) || null;
};

TreeState.prototype.getExplicitSelections = function () {
  return new Map(this.explicitSelections);
};

TreeState.prototype._cascadeDown = function (node, checked) {
  for (var i = 0; i < node.children.length; i++) {
    var child = node.children[i];
    child.checked = checked;
    child.indeterminate = false;
    this._cascadeDown(child, checked);
  }
};

TreeState.prototype._cascadeUp = function (startNode) {
  var current = startNode;
  while (current.parent) {
    var parent = current.parent;
    var children = parent.children;

    var allChecked =
      children.length > 0 &&
      children.every(function (c) {
        return c.checked;
      });
    var someChecked = children.some(function (c) {
      return c.checked || c.indeterminate;
    });

    // Appearance only: a parent riding along on its children reads as
    // indeterminate, explicitSelections is unaffected.
    var showsAsChecked =
      this.collapseToParent || this.explicitSelections.has(parent.id);
    if (allChecked && showsAsChecked) {
      parent.checked = true;
      parent.indeterminate = false;
    } else if (someChecked) {
      parent.checked = false;
      parent.indeterminate = true;
    } else {
      parent.checked = false;
      parent.indeterminate = false;
    }

    current = parent;
  }
};

TreeState.prototype._promoteCheckedChildren = function (node) {
  for (var i = 0; i < node.children.length; i++) {
    var child = node.children[i];
    if (child.checked && !child.indeterminate) {
      this.explicitSelections.set(child.id, this._getLabel(child));
    } else if (child.indeterminate) {
      this._promoteCheckedChildren(child);
    }
  }
};

// Mirror of _demoteAncestors: stops at the first partly checked parent, which
// still needs its children named.
TreeState.prototype._promoteAncestors = function (node) {
  if (!this.collapseToParent) return;
  var current = node;
  while (current.parent) {
    var parent = current.parent;
    if (!parent.checked || parent.indeterminate) return;
    this.explicitSelections.set(parent.id, this._getLabel(parent));
    this._forEachDescendant(
      parent,
      function (desc) {
        this.explicitSelections.delete(desc.id);
      }.bind(this),
    );
    current = parent;
  }
};

TreeState.prototype._demoteAncestors = function (node) {
  var current = node;
  while (current.parent) {
    var parent = current.parent;
    if (this.explicitSelections.has(parent.id)) {
      this.explicitSelections.delete(parent.id);
      this._promoteCheckedChildren(parent);
    }
    current = parent;
  }
};

TreeState.nodeMatches = function (node, q) {
  var query = q.toLowerCase();
  if (node.label && node.label.toLowerCase().includes(query)) return true;
  if (node.abbreviations) {
    for (var i = 0; i < node.abbreviations.length; i++) {
      if (node.abbreviations[i].toLowerCase().includes(query)) return true;
    }
  }
  return false;
};

TreeState.collectMatches = function (nodes, q, result) {
  if (!result) result = [];
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i];
    if (!node.group && !node.self && TreeState.nodeMatches(node, q)) {
      result.push(node);
    }
    if (node.children) TreeState.collectMatches(node.children, q, result);
  }
  return result;
};

TreeState.prototype._getLabel = function (node) {
  var text = node.label;
  if (node.self) text = 'Direct onder "' + text + '"';
  return text;
};

TreeState.prototype._forEachDescendant = function (node, fn) {
  for (var i = 0; i < node.children.length; i++) {
    fn(node.children[i]);
    this._forEachDescendant(node.children[i], fn);
  }
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = TreeState;
} else {
  window.TreeState = TreeState;
}
