// Auto-hide flash messages: fade out after a delay, pause on hover, and remove
// the element once the fade-out animation ends. Flash messages are only
// rendered on full page loads, so wiring this up on load is enough.
(function () {
  var el = document.getElementById("flash-messages");
  if (!el) return;
  var timeout = setTimeout(function () {
    el.classList.add("flash-messages--hiding");
  }, 5000);
  el.addEventListener("mouseenter", function () {
    clearTimeout(timeout);
  });
  el.addEventListener("mouseleave", function () {
    timeout = setTimeout(function () {
      el.classList.add("flash-messages--hiding");
    }, 2000);
  });
  el.addEventListener("animationend", function (e) {
    if (e.animationName === "flash-fade-out") el.remove();
  });
})();
