// Stops nldd-* elements carrying both href and hx-get from navigating. The href
// is there for link semantics, but the anchor in the shadow root navigates and
// wins, throwing the htmx response away with the page. Capture phase, so this
// runs first; only the default action is suppressed, so htmx still sees it.
(function () {
  "use strict";

  document.addEventListener(
    "click",
    (e) => {
      // Modified clicks are deliberate "open elsewhere" gestures — leave them
      // to the browser so the href keeps working as a link.
      if (
        e.defaultPrevented ||
        e.metaKey ||
        e.ctrlKey ||
        e.shiftKey ||
        e.altKey ||
        e.button !== 0
      ) {
        return;
      }
      const host = window.wiesClosestInPath(
        e,
        (el) =>
          el.localName.startsWith("nldd-") &&
          el.hasAttribute("href") &&
          (el.hasAttribute("hx-get") || el.hasAttribute("hx-post")),
      );
      if (host) e.preventDefault();
    },
    true,
  );
})();
