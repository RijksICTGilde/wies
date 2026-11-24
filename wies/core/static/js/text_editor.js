// autofocus on nldd-text-editor does nothing before its CodeMirror view exists
// (focus() is a no-op until then), so wait for the render after a swap.
(function () {
  "use strict";

  function focusAutofocused(root) {
    var editor =
      root.querySelector && root.querySelector("nldd-text-editor[autofocus]");
    if (!editor) return;
    customElements
      .whenDefined("nldd-text-editor")
      .then(function () {
        return editor.updateComplete;
      })
      .then(function () {
        editor.focus();
      });
  }

  document.addEventListener("htmx:afterSettle", function (event) {
    if (event.detail && event.detail.target)
      focusAutofocused(event.detail.target);
  });
})();
