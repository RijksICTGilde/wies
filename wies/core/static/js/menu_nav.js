// Logging out is a POST, so it cannot be an href; the menu item sits in a
// shadow root and cannot be wrapped in a form.
const HREF_CARRIERS = new Set(["nldd-menu-item", "nldd-icon-button"]);

// Posts to the URL with the csrf token already in the markup, plus `fields`.
function submitPost(url, fields = {}) {
  const token = document.querySelector(
    'input[name="csrfmiddlewaretoken"]',
  )?.value;
  const form = document.createElement("form");
  form.method = "post";
  form.action = url;
  const entries = { csrfmiddlewaretoken: token || "", ...fields };
  for (const [name, value] of Object.entries(entries)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}

document.addEventListener("click", (e) => {
  const carrier = e
    .composedPath()
    .find(
      (el) =>
        el instanceof Element &&
        HREF_CARRIERS.has(el.localName) &&
        el.dataset &&
        (el.dataset.href || el.dataset.logoutUrl || el.dataset.postUrl),
    );
  if (!carrier) return;
  if (carrier.dataset.logoutUrl) submitPost(carrier.dataset.logoutUrl);
  else if (carrier.dataset.postUrl)
    submitPost(carrier.dataset.postUrl, {
      terug: carrier.dataset.postReturn || "/",
    });
  else window.location.href = carrier.dataset.href;
});

// The staff switch in the user menu. On click rather than change: a click on
// the knob leaves the change event inside the switch's shadow root. A label
// click also clicks the knob, hence the once-only guard.
document.addEventListener("click", (e) => {
  const field = e
    .composedPath()
    .find(
      (el) =>
        el instanceof Element &&
        el.localName === "nldd-switch-field" &&
        el.dataset.postUrl,
    );
  if (!field || field.dataset.posting) return;
  field.dataset.posting = "1";
  // Long enough to see the knob move before the reload.
  setTimeout(
    () =>
      submitPost(field.dataset.postUrl, {
        terug: field.dataset.postReturn || "/",
      }),
    350,
  );
});
