// Behaviour for inline-edit display partials.
//
// 1. Toast notification on successful save (listens for HX-Trigger: inline-edit-saved).
// 2. "Toon meer / Toon minder" toggle on long text fields.
// Both use delegated listeners that survive HTMX swaps.

function showSavedToast() {
  // Reuse the flash-messages toast pattern from flash_messages.html.
  const prev = document.getElementById("flash-messages");
  if (prev) prev.remove();

  const container = document.createElement("div");
  container.className = "flash-messages";
  container.id = "flash-messages";
  container.innerHTML =
    '<div class="rvo-alert rvo-alert--success rvo-alert--padding-md" role="alert">' +
    '  <div class="rvo-alert__container">' +
    '    <span class="utrecht-icon rvo-icon rvo-icon-bevestiging rvo-status-icon rvo-status-icon-bevestiging rvo-icon--xl" role="img" aria-label="Bevestiging"></span>' +
    '    <div class="rvo-alert-text">Opgeslagen</div>' +
    "  </div>" +
    "</div>";
  // Append to dialog if open (dialogs render in top-layer, above body),
  // otherwise append to body.
  const dialog = document.querySelector("dialog[open]");
  (dialog || document.body).appendChild(container);

  let timeout = setTimeout(
    () => container.classList.add("flash-messages--hiding"),
    3000,
  );
  container.addEventListener("mouseenter", () => clearTimeout(timeout));
  container.addEventListener("mouseleave", () => {
    timeout = setTimeout(
      () => container.classList.add("flash-messages--hiding"),
      2000,
    );
  });
  container.addEventListener("animationend", (e) => {
    if (e.animationName === "flash-fade-out") container.remove();
  });
}

// Show toast after successful inline-edit save.
document.addEventListener("htmx:afterSettle", (event) => {
  const saved = document.querySelector("[data-just-saved]");
  if (saved) {
    saved.removeAttribute("data-just-saved");
    showSavedToast();
  }
});

document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".inline-edit-show-more");
  if (!toggle) return;

  const wrapper = toggle.parentElement;
  if (!wrapper) return;
  // Template uses `inline-edit-long-text__*` for the value spans
  // (the toggle button itself uses `inline-edit-show-more__*`).
  const truncated = wrapper.querySelector(".inline-edit-long-text__truncated");
  const full = wrapper.querySelector(".inline-edit-long-text__full");
  const icon = toggle.querySelector(".inline-edit-show-more__icon");
  const label = toggle.querySelector(".inline-edit-show-more__label");
  if (!truncated || !full || !icon || !label) return;

  const expanded = full.hidden === false;
  truncated.hidden = !expanded;
  full.hidden = expanded;
  icon.textContent = expanded ? "+" : "−";
  label.textContent = expanded ? "Toon meer" : "Toon minder";
});
