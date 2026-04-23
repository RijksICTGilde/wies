// NDD ↔ HTMX bridge
// ----------------------------------------------------------------------------
// NDD componenten (web components met Shadow DOM) emitteren events met
// composed:false. Die events sterven aan de shadow root en bereiken
// document/form niet. Plus: HTMX hx-include ziet alleen built-in form
// elementen, geen custom elements.
//
// Deze bridge:
//   1. Hangt change/input listeners aan elke ndd-* form input zodat we
//      events kunnen opvangen voordat ze verloren gaan.
//   2. Spiegelt ndd-checkbox-field state naar standaard <input type="hidden">
//      siblings binnen [data-ndd-fieldset] zodat hx-include die meeneemt.
//   3. Spiegelt ndd-search-field naar #ndd-search-hidden met debounce.
//   4. Spiegelt ndd-text-field (incl. type=date) als hidden input naast zich.
//   5. Re-dispatcht een synthetische `change` op een hidden input zodat
//      HTMX's hx-trigger="change from:[data-filter-input]" afvuurt.
//   6. MutationObserver gescoped op .ndd-app vangt nieuwe NDD elementen
//      (ook na HTMX swaps).
//   7. Click bridge voor ndd-button met hx-* attributen.
//   8. Dismiss handler voor ndd-token chips → verwijdert filter.
//   9. Sidebar collapse toggle.
// ----------------------------------------------------------------------------

(function () {
  "use strict";

  const NDD_CHECKBOX =
    "ndd-checkbox-field, ndd-switch-field, input[type='checkbox'][data-ndd-input]";
  const NDD_TEXT = "ndd-text-field";
  const NDD_SEARCH = "ndd-search-field";

  // --- ndd-checkbox-field -> hidden input mirror ---------------------
  function rebuildCheckboxesIn(fieldset) {
    const name = fieldset.dataset.name;
    if (!name) return;
    const slot = fieldset.querySelector("[data-hidden-inputs]");
    if (!slot) return;
    slot.innerHTML = "";
    fieldset
      .querySelectorAll("ndd-checkbox-field, input[type='checkbox']")
      .forEach((cb) => {
        const checked =
          cb.checked === true ||
          (cb.checked === undefined && cb.hasAttribute("checked"));
        if (checked) {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = name;
          input.value = cb.getAttribute("value") || "";
          input.setAttribute("data-filter-input", "");
          slot.appendChild(input);
        }
      });
  }

  function dispatchFormChange(form) {
    if (!form) return;
    // Triggert hx-trigger="change from:[data-filter-input]" op de form.
    const sentinel = form.querySelector("[data-filter-input]");
    (sentinel || form).dispatchEvent(new Event("change", { bubbles: true }));
  }

  function attachCheckbox(el) {
    if (el.__nddBridgeAttached) return;
    el.__nddBridgeAttached = true;
    const onChange = () => {
      const fieldset = el.closest("[data-ndd-fieldset]");
      if (fieldset) rebuildCheckboxesIn(fieldset);
      const form = el.closest("form");
      if (form) dispatchFormChange(form);
    };
    el.addEventListener("change", onChange);
    el.addEventListener("input", onChange);
  }

  // --- ndd-text-field (date etc.) -> hidden input mirror ------------
  function attachTextField(el) {
    if (el.__nddBridgeAttached) return;
    el.__nddBridgeAttached = true;
    const name = el.getAttribute("name");
    if (!name) return;
    // Schrijf hidden input direct na het ndd-text-field element.
    let hidden =
      el.parentElement &&
      el.parentElement.querySelector(
        `input[type="hidden"][name="${CSS.escape(name)}"][data-bridged]`,
      );
    if (!hidden) {
      hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = name;
      hidden.setAttribute("data-filter-input", "");
      hidden.setAttribute("data-bridged", "");
      el.insertAdjacentElement("afterend", hidden);
    }
    const sync = () => {
      const value =
        el.value !== undefined ? el.value : el.getAttribute("value") || "";
      if (hidden.value !== value) {
        hidden.value = value;
        const form = el.closest("form");
        if (form) dispatchFormChange(form);
      }
    };
    sync(); // initial
    el.addEventListener("change", sync);
    el.addEventListener("input", sync);
  }

  // --- ndd-search-field -> #ndd-search-hidden -----------------------
  function attachSearchField(el) {
    if (el.__nddSearchAttached) return;
    el.__nddSearchAttached = true;
    const hidden = document.getElementById("ndd-search-hidden");
    if (!hidden) return;
    let timer = null;
    const sync = () => {
      const value =
        el.value !== undefined ? el.value : el.getAttribute("value") || "";
      if (hidden.value !== value) {
        hidden.value = value;
        hidden.dispatchEvent(new Event("change", { bubbles: true }));
      }
    };
    el.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(sync, 500);
    });
    el.addEventListener("change", () => {
      clearTimeout(timer);
      sync();
    });
  }

  // --- ndd-token dismiss -> verwijder filter ------------------------
  function removeFilter(name, value) {
    const form = document.getElementById("ndd-filter-form");
    if (!form) return;

    if (name === "zoek") {
      const hidden = document.getElementById("ndd-search-hidden");
      const searchField = document.querySelector("[data-ndd-search-input]");
      if (hidden) hidden.value = "";
      if (searchField) {
        try {
          searchField.value = "";
        } catch (_) {}
      }
      dispatchFormChange(form);
      return;
    }

    // Multi-select: vink corresponderende ndd-checkbox-field uit.
    const fieldset = form.querySelector(
      `[data-ndd-fieldset][data-name="${CSS.escape(name)}"]`,
    );
    if (fieldset && value !== null) {
      const cb = Array.from(
        fieldset.querySelectorAll("ndd-checkbox-field, input[type='checkbox']"),
      ).find((el) => el.getAttribute("value") === value);
      if (cb) {
        try {
          cb.checked = false;
        } catch (_) {}
        cb.removeAttribute("checked");
        rebuildCheckboxesIn(fieldset);
        dispatchFormChange(form);
        return;
      }
    }

    // Org filters (modal-managed): verwijder hidden input direct.
    const orgContainer = document.getElementById("ndd-org-filter-inputs");
    if (orgContainer) {
      const inputs = Array.from(
        orgContainer.querySelectorAll(`input[name="${CSS.escape(name)}"]`),
      );
      inputs.forEach((input) => {
        if (value === null || input.value === value) input.remove();
      });
      dispatchFormChange(form);
    }
  }

  // ndd-token "dismiss" event is composed:true (volgens NDD code)
  function setupTokenDismiss() {
    document.addEventListener("dismiss", (e) => {
      const path = e.composedPath();
      const token = path.find(
        (el) =>
          el instanceof Element && el.tagName?.toLowerCase() === "ndd-token",
      );
      if (!token) return;
      if (token.dataset.nddDismiss !== "filter") return;
      removeFilter(token.dataset.filterName, token.dataset.filterValue || null);
    });
  }

  // --- Click bridge voor ndd-* hosts met hx-* attributes ------------
  function setupClickBridge() {
    document.addEventListener("click", (e) => {
      const path = e.composedPath();
      const host = path.find(
        (el) =>
          el instanceof Element &&
          el.tagName &&
          el.tagName.toLowerCase().startsWith("ndd-") &&
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
      // hx-include support
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
      // Gebruik source zodat HTMX correcte headers (HX-Current-URL etc.) meestuurt
      opts.source = host;
      window.htmx.ajax(verb, url, opts);
    });
  }

  // --- Sidebar collapse toggle --------------------------------------
  function setupSidebarToggle() {
    const sheet = document.getElementById("ndd-filter-sheet");
    const pane = document.getElementById("ndd-sidebar-pane");
    const isMobile = () => window.matchMedia("(max-width: 1007px)").matches;

    document.addEventListener("click", (e) => {
      const path = e.composedPath();
      const btn = path.find(
        (el) => el instanceof Element && el.id === "ndd-sidebar-toggle",
      );
      if (!btn) return;

      if (isMobile() && sheet) {
        // Mobile: verplaats sidebar content naar sheet en open
        const sheetContent = document.getElementById(
          "ndd-filter-sheet-content",
        );
        const sidebarBody = pane?.querySelector(".ndd-sidebar-pane__body");
        if (sheetContent && sidebarBody) {
          while (sidebarBody.firstChild) {
            sheetContent.appendChild(sidebarBody.firstChild);
          }
          sheet.show();
          sheet.addEventListener(
            "close",
            () => {
              while (sheetContent.children.length > 1) {
                sidebarBody.appendChild(sheetContent.lastChild);
              }
            },
            { once: true },
          );
        }
      } else if (pane) {
        // Desktop: toggle sidebar
        pane.classList.toggle("collapsed");
      }
    });
  }

  // --- Scan + observe -----------------------------------------------
  function scan(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll(NDD_CHECKBOX).forEach(attachCheckbox);
    root.querySelectorAll(NDD_TEXT).forEach(attachTextField);
    root.querySelectorAll(NDD_SEARCH).forEach(attachSearchField);
  }

  function init() {
    const app = document.querySelector(".ndd-app");
    if (!app) return;

    scan(app);

    new MutationObserver((mutations) => {
      for (const m of mutations) {
        m.addedNodes.forEach((n) => {
          if (n.nodeType !== 1) return;
          if (n.matches?.(NDD_CHECKBOX)) attachCheckbox(n);
          if (n.matches?.(NDD_TEXT)) attachTextField(n);
          if (n.matches?.(NDD_SEARCH)) attachSearchField(n);
          scan(n);
        });
      }
    }).observe(app, { childList: true, subtree: true });

    setupClickBridge();
    setupTokenDismiss();
    setupFilterCollapseAndToggle();
    setupSidebarToggle();
  }

  // --- Filter groep in/uitklappen + "Toon meer/minder" ----------------
  function setupFilterCollapseAndToggle() {
    document.addEventListener("click", (e) => {
      // Header collapse toggle
      const collapseBtn = e.target.closest("[data-ndd-collapse-toggle]");
      if (collapseBtn) {
        e.preventDefault();
        const fieldset = collapseBtn.closest("[data-ndd-collapsible]");
        if (fieldset) fieldset.toggleAttribute("data-collapsed");
        return;
      }

      // "Toon meer / Toon minder" toggle
      const toggleBtn = e.target.closest(".ndd-checkbox-filter__toggle");
      if (toggleBtn) {
        e.preventDefault();
        const extra = toggleBtn.previousElementSibling;
        if (!extra) return;
        const expanding = extra.hidden;
        extra.hidden = !expanding;
        toggleBtn.classList.toggle(
          "ndd-checkbox-filter__toggle--expanded",
          expanding,
        );
        const icon = toggleBtn.querySelector(
          ".ndd-checkbox-filter__toggle-icon",
        );
        const text = toggleBtn.querySelector(
          ".ndd-checkbox-filter__toggle-text",
        );
        if (icon) icon.setAttribute("name", expanding ? "minus" : "plus");
        if (text) text.textContent = expanding ? "Toon minder" : "Toon meer";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
