// Navigatie voor nldd-componenten die een data-href dragen: die componenten
// leveren zelf geen link-gedrag, dus we vangen de click (via composedPath, want
// het element zit in een shadow root) en navigeren. Geldt voor menu-items én
// voor een losse nldd-icon-button — een rijactie die de enige actie is, wordt
// als knop getoond in plaats van in een menu. Extern bestand i.p.v. inline
// <script>, zodat de CSP script-src 'self' kan blijven (geen 'unsafe-inline').
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
