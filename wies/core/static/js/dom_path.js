// Finds the innermost matching element in an event's composed path. Events from
// NLDD components start inside a shadow root, where closest() stops at the
// boundary.
//
// @param {Event} event The event to walk.
// @param {string|function} test A CSS selector, or a predicate on the element.
// @returns {Element|null} The matching element, or null.
window.wiesClosestInPath = function wiesClosestInPath(event, test) {
  const path = event.composedPath();
  const matches =
    typeof test === "function"
      ? test
      : (el) => typeof el.matches === "function" && el.matches(test);
  for (const el of path) {
    if (el instanceof Element && matches(el)) return el;
  }
  return null;
};
