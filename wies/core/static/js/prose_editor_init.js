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

  // --------------------------------------------------------------------------
  // Live character counter for prose fields with a max length.
  //
  // The limit is enforced server-side via CharField.max_length on the stored
  // HTML (markup included). We mirror that here: the editor writes its HTML to
  // the hidden <textarea>, so we count textarea.value.length — the same string
  // the server validates — and show "X / max", going into an over-limit state
  // when exceeded. This is a UX hint; the server is the source of truth.
  // --------------------------------------------------------------------------
  function counterFor(textarea) {
    var max = parseInt(textarea.getAttribute("data-prose-maxlength"), 10);
    if (!max) return;
    var wrapper = textarea.closest(".prose-editor") || textarea.parentElement;
    if (!wrapper || wrapper.querySelector(".prose-editor-counter")) return;

    var counter = document.createElement("div");
    counter.className = "prose-editor-counter";
    wrapper.appendChild(counter);

    function update() {
      var len = textarea.value.length;
      counter.textContent = len + " / " + max;
      counter.classList.toggle("prose-editor-counter--over", len > max);
    }
    update();
    // The editor pushes HTML to the textarea on every edit; "input" on the
    // wrapper catches both editor edits and direct textarea changes.
    wrapper.addEventListener("input", update);
    textarea.addEventListener("input", update);
  }

  function initCounters(root) {
    (root || document)
      .querySelectorAll("textarea[data-prose-maxlength]")
      .forEach(counterFor);
  }

  // Editors initialise asynchronously (and via HTMX swaps); poll briefly so the
  // counter attaches once the .prose-editor wrapper exists, then on each swap.
  initCounters(document);
  var tries = 0;
  var timer = setInterval(function () {
    initCounters(document);
    if (++tries > 20) clearInterval(timer);
  }, 250);
  document.body.addEventListener("htmx:afterSettle", function (e) {
    initCounters(e.detail && e.detail.target ? e.detail.target : document);
  });
});
