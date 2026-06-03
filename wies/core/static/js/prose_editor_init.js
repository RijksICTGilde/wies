/**
 * Initialize django-prose-editor instances on dynamically added DOM nodes.
 *
 * The default.js module only initializes editors found at page load.
 * This MutationObserver picks up textareas added later by HTMX swaps
 * and hands them to the same createEditor function.
 */
document.addEventListener("DOMContentLoaded", function () {
  var sel = "[data-django-prose-editor-default]";
  new MutationObserver(function (mutations) {
    if (!window.DjangoProseEditor) return;
    for (var i = 0; i < mutations.length; i++) {
      var nodes = mutations[i].addedNodes;
      for (var j = 0; j < nodes.length; j++) {
        var node = nodes[j];
        if (node.nodeType !== 1) continue;
        var targets = [];
        if (node.matches && node.matches(sel)) targets.push(node);
        if (node.querySelectorAll)
          targets.push.apply(targets, node.querySelectorAll(sel));
        for (var k = 0; k < targets.length; k++) {
          if (!targets[k].closest(".prose-editor")) {
            window.DjangoProseEditor.createEditor(targets[k]);
          }
        }
      }
    }
  }).observe(document.body, { childList: true, subtree: true });
});
