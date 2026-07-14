// Click bridge for nldd-* hosts with hx-* attributes.
//
// nldd-button and friends are custom elements; a bare hx-get/hx-post on them
// isn't wired by HTMX's own delegated handler (it binds to standard elements).
// This forwards a click on any nldd-* host carrying hx-get/hx-post to
// htmx.ajax, preserving hx-target/hx-swap/hx-include and using the host as
// `source` so HTMX sends the right headers (HX-Current-URL etc.).
(function () {
  "use strict";

  document.addEventListener("click", (e) => {
    const path = e.composedPath();
    const host = path.find(
      (el) =>
        el instanceof Element &&
        el.tagName &&
        el.tagName.toLowerCase().startsWith("nldd-") &&
        (el.hasAttribute("hx-get") || el.hasAttribute("hx-post")),
    );
    if (!host || !window.htmx) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const verb = host.hasAttribute("hx-get") ? "GET" : "POST";
    const url = host.getAttribute("hx-get") || host.getAttribute("hx-post");
    const opts = {};
    const target = host.getAttribute("hx-target");
    if (target) opts.target = target;
    const swap = host.getAttribute("hx-swap");
    if (swap) opts.swap = swap;
    const include = host.getAttribute("hx-include");
    if (include) {
      const values = {};
      document.querySelectorAll(include + " input").forEach((input) => {
        if (input.name && input.value) {
          if (values[input.name] === undefined) values[input.name] = [];
          values[input.name].push(input.value);
        }
      });
      opts.values = values;
    }
    opts.source = host;
    window.htmx.ajax(verb, url, opts);
  });
})();
