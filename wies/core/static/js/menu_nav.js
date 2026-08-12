// Navigation for nldd components carrying data-href: they provide no link
// behaviour themselves, so the click is caught via composedPath (the element
// lives in a shadow root) and navigated manually. External file rather than
// inline <script>, so the CSP can stay script-src 'self'.
const HREF_CARRIERS = new Set(["nldd-menu-item", "nldd-icon-button"]);

// Verstuur een POST naar de gegeven URL met het csrf-token dat al in de markup
// staat. Voor acties die geen GET-navigatie zijn (uitloggen is @require_POST),
// terwijl het menu-item in een shadow root zit en dus niet in een <form> te
// wikkelen is zoals op de "Geen toegang"-pagina.
function submitPost(url) {
  const token = document.querySelector(
    'input[name="csrfmiddlewaretoken"]',
  )?.value;
  const form = document.createElement("form");
  form.method = "post";
  form.action = url;
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "csrfmiddlewaretoken";
  input.value = token || "";
  form.appendChild(input);
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
        (el.dataset.href || el.dataset.logoutUrl),
    );
  if (!carrier) return;
  if (carrier.dataset.logoutUrl) submitPost(carrier.dataset.logoutUrl);
  else window.location.href = carrier.dataset.href;
});
