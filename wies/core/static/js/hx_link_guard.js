// Stops nldd-* elements carrying both href and hx-get from navigating: the
// shadow-root anchor wins and throws the htmx response away with the page.
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
