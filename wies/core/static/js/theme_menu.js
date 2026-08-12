// Display choice from the user menu: apply to <html> and store on the user.
// Only covers the switch itself; after a reload the server renders data-scheme.
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
  // No attribute means the NLDD colours follow prefers-color-scheme.
  if (choice === "system") root.removeAttribute("data-scheme");
  else root.setAttribute("data-scheme", choice);

  // nldd-menu-item type="radio" does not deselect its siblings.
  for (const other of items) other.toggleAttribute("selected", other === item);

  const menu = item.closest("nldd-menu");
  const url = menu && menu.dataset ? menu.dataset.themeUrl : null;
  const token = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (!url || !token) return;

  const body = new FormData();
  body.append("theme", choice);
  body.append("csrfmiddlewaretoken", token.value);
  fetch(url, { method: "POST", body, credentials: "same-origin" }).catch(() => {
    // The screen is already correct; a lost preference is not worth a notice.
  });
});
