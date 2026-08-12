// Innermost element in an event's composed path; closest() stops at a shadow
// boundary, the path does not.
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
