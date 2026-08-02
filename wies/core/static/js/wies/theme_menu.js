// Display choice from the user menu: apply it to <html> right away and store it
// on the user. The server renders data-scheme while building the page, so this
// path only covers the switch itself; after a reload the choice comes from the
// database. External file rather than an inline <script>, so the CSP can keep
// script-src 'self' (no 'unsafe-inline'), same as menu_nav.js.
document.addEventListener("select", (e) => {
  const items = [
    ...document.querySelectorAll("nldd-menu-item[data-theme-choice]"),
  ];
  const item = e
    .composedPath()
    .find((el) => el instanceof Element && items.includes(el));
  if (!item) return;

  const choice = item.dataset.themeChoice;
  const root = document.documentElement;
  // 'system' leaves the choice to the browser: no attribute means the NLDD
  // colours fall back to prefers-color-scheme.
  if (choice === "system") root.removeAttribute("data-scheme");
  else root.setAttribute("data-scheme", choice);

  // nldd-menu-item type="radio" is a controlled prop: the component does not
  // deselect its siblings, so without this the checkmark stays on whatever the
  // server rendered until the next page load.
  for (const other of items) other.toggleAttribute("selected", other === item);

  const menu = item.closest("nldd-menu");
  const url = menu && menu.dataset ? menu.dataset.themeUrl : null;
  const token = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (!url || !token) return;

  const body = new FormData();
  body.append("theme", choice);
  body.append("csrfmiddlewaretoken", token.value);
  fetch(url, { method: "POST", body, credentials: "same-origin" }).catch(() => {
    // The screen is already correct; a failed save only shows up in the next
    // session, with the old choice still in place. No notification: this is a
    // preference, not an action that asks for confirmation.
  });
});
