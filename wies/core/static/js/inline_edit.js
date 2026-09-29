// Inline-edit display partials: a toast on save.

function showSavedToast(label) {
  // nldd-notification relocates itself and runs its own timer. Replacing the
  // previous one stops identical messages from stacking.
  document
    .querySelectorAll("nldd-notification[data-wies-saved]")
    .forEach((el) => el.remove());

  const toast = document.createElement("nldd-notification");
  toast.setAttribute("variant", "success");
  // Editable labels arrive capitalised ("Periode"), so the label leads.
  toast.setAttribute(
    "text",
    label ? `${label} opgeslagen` : "Wijziging opgeslagen",
  );
  toast.setAttribute("data-wies-saved", "");
  document.body.appendChild(toast);
}

// The view sets HX-Trigger-After-Swap: inline-edit-saved on the response.
document.addEventListener("inline-edit-saved", (e) =>
  showSavedToast(e.detail?.label),
);

// The server collapses a rendered description on a guess (source length and
// line count); only the browser knows whether anything is actually hidden.
// A block that fits opens up and loses its toggle.
function uncollapseWhatFits(root) {
  var blocks = root.querySelectorAll
    ? root.querySelectorAll(".wies-long-text--collapsed")
    : [];
  blocks.forEach(function (block) {
    var body = block.querySelector(".wies-long-text__body");
    if (!body || body.scrollHeight > body.clientHeight + 1) return;
    block.classList.remove("wies-long-text--collapsed");
    var toggle = block.querySelector(".inline-edit-show-more");
    if (toggle) toggle.remove();
  });
}

document.addEventListener("htmx:afterSettle", function (event) {
  if (event.detail && event.detail.target)
    uncollapseWhatFits(event.detail.target);
});
// A panel rendered with the page: measure once the components have laid out.
customElements.whenDefined("nldd-rich-text").then(function () {
  requestAnimationFrame(function () {
    uncollapseWhatFits(document);
  });
});
