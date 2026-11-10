// "Toon meer" under the Taken of a cv entry. The server shows it only past a
// fixed length; on a narrow screen the three-line clamp cuts a shorter text
// too, so the toggle has to follow what the browser actually clamps.

(function () {
  // An open entry hides its preview and keeps the toggle for "Toon minder".
  function syncClampedToggle(preview, toggle) {
    if (preview.hidden) return;
    toggle.hidden = preview.scrollHeight <= preview.clientHeight;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { syncClampedToggle: syncClampedToggle };
    return;
  }

  function toggleFor(preview) {
    return preview.parentElement.querySelector("[data-reveal-when-clamped]");
  }

  // A size change covers every reason the clamp can start or stop cutting: a
  // resize, zoom, and the side panel opening after the swap that filled it.
  var observer = new ResizeObserver(function (entries) {
    entries.forEach(function (entry) {
      var preview = entry.target;
      var toggle = preview.isConnected && toggleFor(preview);
      if (toggle) syncClampedToggle(preview, toggle);
      else observer.unobserve(preview);
    });
  });

  function observeAll(root) {
    root.querySelectorAll("[data-cv-preview]").forEach(function (preview) {
      observer.observe(preview);
    });
  }

  observeAll(document);
  // The whole document: an out-of-band swap brings cards outside the target,
  // and observing an element twice is a no-op.
  document.addEventListener("htmx:afterSettle", function () {
    observeAll(document);
  });
})();
