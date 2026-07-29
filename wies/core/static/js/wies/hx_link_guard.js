// Stops nldd-* elements that carry BOTH href and hx-get from navigating.
//
// Rows like nldd-list-item keep a real href for link semantics (hover, focus,
// middle-click, keyboard) and let htmx open a modal instead. htmx 2 issues the
// hx-get itself, but the anchor inside the component's shadow root still
// navigates, and the navigation wins — the modal is thrown away with the page.
//
// Capture phase, so this runs before the shadow anchor acts on the click.
// Only the default action is suppressed; the event keeps propagating so htmx
// still sees it and performs the request.
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
      const host = e
        .composedPath()
        .find(
          (el) =>
            el instanceof Element &&
            el.tagName?.toLowerCase().startsWith("nldd-") &&
            el.hasAttribute("href") &&
            (el.hasAttribute("hx-get") || el.hasAttribute("hx-post")),
        );
      if (host) e.preventDefault();
    },
    true,
  );
})();
