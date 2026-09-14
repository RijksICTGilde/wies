// Logging out is a POST, so it cannot be an href; the menu item sits in a
// shadow root and cannot be wrapped in a form.
const HREF_CARRIERS = new Set(["nldd-menu-item", "nldd-icon-button"]);

// Posts to the URL with the csrf token already in the markup; `fields` are
// extra hidden inputs (name → value).
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
