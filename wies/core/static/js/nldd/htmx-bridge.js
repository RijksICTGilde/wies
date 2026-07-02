// NDD ↔ HTMX bridge
// ----------------------------------------------------------------------------
// NDD componenten (web components met Shadow DOM) emitteren events met
// composed:false. Die events sterven aan de shadow root en bereiken
// document/form niet. Plus: HTMX hx-include ziet alleen built-in form
// elementen, geen custom elements.
//
// Deze bridge:
//   1. Hangt change/input listeners aan elke nldd-* form input zodat we
//      events kunnen opvangen voordat ze verloren gaan.
//   2. Spiegelt nldd-checkbox-field state naar standaard <input type="hidden">
//      siblings binnen [data-nldd-fieldset] zodat hx-include die meeneemt.
//   3. Spiegelt nldd-search-field naar #nldd-search-hidden met debounce.
//   4. Spiegelt nldd-text-field (incl. type=date) als hidden input naast zich.
//   5. Re-dispatcht een synthetische `change` op een hidden input zodat
//      HTMX's hx-trigger="change from:[data-filter-input]" afvuurt.
//   6. MutationObserver gescoped op .nldd-app vangt nieuwe NDD elementen
//      (ook na HTMX swaps).
//   7. Click bridge voor nldd-button met hx-* attributen.
//   8. Dismiss handler voor nldd-token chips → verwijdert filter.
//   9. Sidebar collapse toggle.
// ----------------------------------------------------------------------------

(function () {
  "use strict";

  const NDD_CHECKBOX =
    "nldd-checkbox-field, nldd-switch-field, input[type='checkbox'][data-nldd-input]";
  const NDD_TEXT = "nldd-text-field";
  const NDD_SEARCH = "nldd-search-field";

  // --- nldd-checkbox-field -> hidden input mirror ---------------------
  function rebuildCheckboxesIn(fieldset) {
    const name = fieldset.dataset.name;
    if (!name) return;
    const slot = fieldset.querySelector("[data-hidden-inputs]");
    if (!slot) return;
    slot.innerHTML = "";
    fieldset
      .querySelectorAll("nldd-checkbox-field, input[type='checkbox']")
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
      const fieldset = el.closest("[data-nldd-fieldset]");
      if (fieldset) rebuildCheckboxesIn(fieldset);
      const form = el.closest("form");
      if (form) dispatchFormChange(form);
    };
    el.addEventListener("change", onChange);
    el.addEventListener("input", onChange);
  }

  // --- nldd-text-field (date etc.) -> hidden input mirror ------------
  function attachTextField(el) {
    if (el.__nddBridgeAttached) return;
    el.__nddBridgeAttached = true;
    const name = el.getAttribute("name");
    if (!name) return;
    // Schrijf hidden input direct na het nldd-text-field element.
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

  // --- nldd-search-field: suggestions + Enter-commit ------------------
  // nldd-search-field fires: `input` (typing), `search` (Enter / search
  // button), `change` (blur). We show live suggestions while typing and
  // commit the search (write hidden -> run filter, hide suggestions, blur)
  // on `search`. Committing via a suggestion click routes through here too.
  function suggestionsBox() {
    return document.getElementById("nldd-search-suggestions");
  }
  function hideSuggestions() {
    const box = suggestionsBox();
    if (box) box.innerHTML = "";
  }
  function commitSearch(el, value) {
    const hidden = document.getElementById("nldd-search-hidden");
    if (!hidden) return;
    if (typeof value === "string") {
      try {
        el.value = value;
      } catch (_) {}
    }
    const v = value !== undefined ? value : el.value || "";
    hidden.value = v;
    hidden.dispatchEvent(new Event("change", { bubbles: true }));
    hideSuggestions();
    // Blur the inner input so the dropdown doesn't reopen on focus.
    try {
      el.blur();
      el.shadowRoot?.querySelector("input")?.blur();
    } catch (_) {}
  }

  function attachSearchField(el) {
    if (el.__nddSearchAttached) return;
    el.__nddSearchAttached = true;
    let timer = null;

    el.addEventListener("input", (e) => {
      const term = (e.detail?.value ?? el.value ?? "").trim();
      clearTimeout(timer);
      if (!term) {
        hideSuggestions();
        return;
      }
      timer = setTimeout(() => {
        const box = suggestionsBox();
        if (!box || !window.htmx) return;
        window.htmx.ajax("GET", `/zoek-suggesties/?zoek=${encodeURIComponent(term)}`, {
          target: "#nldd-search-suggestions",
          swap: "innerHTML",
        });
      }, 250);
    });

    // Enter / search button commits immediately.
    el.addEventListener("search", (e) => {
      commitSearch(el, (e.detail?.value ?? el.value ?? "").trim());
    });
    // Clearing the field (× dismiss) empties the search.
    el.addEventListener("change", (e) => {
      const v = (e.detail?.value ?? el.value ?? "").trim();
      if (!v) commitSearch(el, "");
    });
  }

  function setupSearchSuggestionClicks() {
    document.addEventListener("click", (e) => {
      const btn = e.composedPath().find(
        (x) => x instanceof Element && x.classList?.contains("search-suggestion"),
      );
      if (!btn) return;
      const searchField = document.querySelector("[data-nldd-search-input]");

      // "Zoeken op …" commits the current search term.
      if (btn.hasAttribute("data-search-commit")) {
        if (searchField) commitSearch(searchField, (searchField.value || "").trim());
        return;
      }

      // Org suggestion: add it as an org filter and clear the search.
      const orgId = btn.dataset.orgId;
      if (orgId) {
        const form = document.getElementById("nldd-filter-form");
        const container = document.getElementById("nldd-org-filter-inputs");
        if (container && !container.querySelector(`input[name="org"][value="${CSS.escape(orgId)}"]`)) {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = "org";
          input.value = orgId;
          input.setAttribute("data-filter-input", "");
          input.setAttribute("data-label", btn.dataset.orgLabel || "");
          container.appendChild(input);
        }
        if (searchField) {
          try {
            searchField.value = "";
          } catch (_) {}
        }
        const hidden = document.getElementById("nldd-search-hidden");
        if (hidden) hidden.value = "";
        hideSuggestions();
        if (form) dispatchFormChange(form);
      }
    });

    // Click outside closes the suggestions.
    document.addEventListener("click", (e) => {
      const path = e.composedPath();
      const inSearch = path.some(
        (x) =>
          x instanceof Element &&
          (x.id === "nldd-search-suggestions" ||
            x.hasAttribute?.("data-nldd-search-input")),
      );
      if (!inSearch) hideSuggestions();
    });
  }

  // --- nldd-token dismiss -> verwijder filter ------------------------
  function removeFilter(name, value) {
    const form = document.getElementById("nldd-filter-form");
    if (!form) return;

    if (name === "zoek") {
      const hidden = document.getElementById("nldd-search-hidden");
      const searchField = document.querySelector("[data-nldd-search-input]");
      if (hidden) hidden.value = "";
      if (searchField) {
        try {
          searchField.value = "";
        } catch (_) {}
      }
      dispatchFormChange(form);
      return;
    }

    // Multi-select: uncheck the matching checkbox. "labels" repeats per
    // category, so several fieldsets share data-name="labels" — search ALL
    // of them for the value, not just the first.
    if (value !== null) {
      const fieldsets = form.querySelectorAll(
        `[data-nldd-fieldset][data-name="${CSS.escape(name)}"]`,
      );
      for (const fieldset of fieldsets) {
        const cb = Array.from(
          fieldset.querySelectorAll(
            "nldd-checkbox-field, input[type='checkbox']",
          ),
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
    }

    // Org filters (modal-managed): verwijder hidden input direct.
    const orgContainer = document.getElementById("nldd-org-filter-inputs");
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

  // nldd-token "dismiss" event is composed:true (volgens NDD code)
  function setupTokenDismiss() {
    document.addEventListener("dismiss", (e) => {
      const path = e.composedPath();
      const token = path.find(
        (el) =>
          el instanceof Element && el.tagName?.toLowerCase() === "nldd-token",
      );
      if (!token) return;
      if (token.dataset.nlddDismiss !== "filter") return;
      removeFilter(token.dataset.filterName, token.dataset.filterValue || null);
    });
  }

  // --- "Wis alle filters" -------------------------------------------
  // Clears search, every checkbox group and the org filter in one go,
  // then re-runs the filter once.
  function clearAllFilters() {
    const form = document.getElementById("nldd-filter-form");
    if (!form) return;

    // Search
    const hidden = document.getElementById("nldd-search-hidden");
    const searchField = document.querySelector("[data-nldd-search-input]");
    if (hidden) hidden.value = "";
    if (searchField) {
      try {
        searchField.value = "";
      } catch (_) {}
    }

    // Checkbox groups
    form.querySelectorAll("[data-nldd-fieldset]").forEach((fieldset) => {
      fieldset
        .querySelectorAll("nldd-checkbox-field, input[type='checkbox']")
        .forEach((cb) => {
          try {
            cb.checked = false;
          } catch (_) {}
          cb.removeAttribute("checked");
        });
      rebuildCheckboxesIn(fieldset);
    });

    // Org filter (modal-managed hidden inputs)
    const orgContainer = document.getElementById("nldd-org-filter-inputs");
    if (orgContainer) orgContainer.innerHTML = "";

    dispatchFormChange(form);
  }

  function setupClearAllFilters() {
    document.addEventListener("click", (e) => {
      const btn = e.composedPath().find(
        (el) =>
          el instanceof Element &&
          el.hasAttribute &&
          el.hasAttribute("data-nldd-clear-all"),
      );
      if (!btn) return;
      e.preventDefault();
      clearAllFilters();
    });
  }

  // --- Opdrachtgever quick checkboxes -------------------------------
  // The top-3 org quick options in the sidebar each carry their own param
  // (org / org_self / org_type). Ticking one writes/removes a hidden input
  // in #nldd-org-filter-inputs and re-runs the filter — no modal needed.
  function setupOrgQuickOptions() {
    document.addEventListener("change", (e) => {
      const cb = e.target;
      if (
        !(cb instanceof HTMLInputElement) ||
        !cb.classList.contains("org-filter-quick__checkbox")
      ) {
        return;
      }
      const form = document.getElementById("nldd-filter-form");
      const container = document.getElementById("nldd-org-filter-inputs");
      if (!form || !container) return;
      const param = cb.dataset.orgParam || "org";
      const value = cb.value;
      const existing = Array.from(
        container.querySelectorAll(`input[name="${CSS.escape(param)}"]`),
      ).find((el) => el.value === value);
      if (cb.checked && !existing) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = param;
        input.value = value;
        input.setAttribute("data-filter-input", "");
        input.setAttribute("data-label", cb.dataset.orgLabel || "");
        container.appendChild(input);
      } else if (!cb.checked && existing) {
        existing.remove();
      }
      dispatchFormChange(form);
    });
  }

  // --- Click bridge voor nldd-* hosts met hx-* attributes ------------
  function setupClickBridge() {
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

  // --- Filter options "Meer" modal ----------------------------------
  // A sidebar group's "Meer" button opens filter_options_modal.html into
  // #nldd-filter-options-modal-container. Ticking there is deferred: only
  // "Filter toepassen" writes the selection back to the sidebar group and
  // re-runs the filter. Closing (× / Escape / Annuleren) discards.
  function setupFilterOptionsModal() {
    const container = document.getElementById(
      "nldd-filter-options-modal-container",
    );

    function currentModal() {
      return document.getElementById("nldd-filter-options-modal");
    }
    function closeModal() {
      const modal = currentModal();
      if (modal && modal.hide) modal.hide();
      if (container) container.innerHTML = "";
    }

    // Open the modal once htmx swaps it in. The <nldd-window> is a Lit
    // component: right after the swap its shadow <dialog> may not exist yet,
    // so show() would no-op. Wait for the element to upgrade + finish its
    // first render (updateComplete) before opening; fall back to a rAF.
    function openWhenReady(modal, attempt) {
      if (!modal) return;
      const tryShow = () => {
        if (typeof modal.show === "function" && modal.shadowRoot?.querySelector("dialog")) {
          modal.show();
        } else if ((attempt || 0) < 20) {
          requestAnimationFrame(() => openWhenReady(modal, (attempt || 0) + 1));
        }
      };
      if (modal.updateComplete && typeof modal.updateComplete.then === "function") {
        modal.updateComplete.then(tryShow);
      } else {
        tryShow();
      }
    }

    document.body.addEventListener("htmx:afterSwap", (e) => {
      const t = e.target;
      if (
        t &&
        (t.id === "nldd-filter-options-modal-container" ||
          (t.closest &&
            t.closest("#nldd-filter-options-modal-container")))
      ) {
        openWhenReady(currentModal(), 0);
      }
    });

    document.addEventListener("click", (e) => {
      const path = e.composedPath();

      // Cancel / close
      if (
        path.some(
          (el) =>
            el instanceof Element &&
            el.getAttribute &&
            el.getAttribute("data-nldd-action") === "filter-options-close",
        )
      ) {
        closeModal();
        return;
      }

      // Apply
      const applyBtn = path.find(
        (el) => el instanceof Element && el.id === "filter-options-apply-btn",
      );
      if (!applyBtn) return;

      const modal = currentModal();
      if (!modal) return;
      const groupId = modal.getAttribute("data-group-id");
      const values = [...modal.querySelectorAll(".nldd-filter-options-modal__checkbox")]
        .filter((cb) => cb.checked)
        .map((cb) => cb.value);

      const fieldset = document.querySelector(
        `[data-nldd-fieldset][data-group-id="${CSS.escape(groupId)}"]`,
      );
      const form = document.getElementById("nldd-filter-form");
      if (fieldset) {
        // Reflect the modal selection onto the sidebar's inline checkboxes...
        fieldset
          .querySelectorAll(".nldd-filter-option__checkbox")
          .forEach((cb) => {
            cb.checked = values.includes(cb.value);
          });
        // ...and write the full selection (incl. options not shown inline)
        // straight into the hidden-inputs slot so hx-include picks them up.
        const slot = fieldset.querySelector("[data-hidden-inputs]");
        const name = fieldset.dataset.name;
        if (slot && name) {
          slot.innerHTML = "";
          for (const v of values) {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = name;
            input.value = v;
            input.setAttribute("data-filter-input", "");
            slot.appendChild(input);
          }
        }
      }
      closeModal();
      if (form) dispatchFormChange(form);
    });

    // Live search within the modal.
    document.addEventListener("input", (e) => {
      const path = e.composedPath();
      const search = path.find(
        (el) => el instanceof Element && el.id === "filter-options-search",
      );
      if (!search) return;
      const term = (search.value || "").toLowerCase().trim();
      const modal = currentModal();
      if (!modal) return;
      modal
        .querySelectorAll(".nldd-filter-options-modal__option")
        .forEach((opt) => {
          const label = opt.getAttribute("data-option-label") || "";
          opt.hidden = term && !label.includes(term);
        });
    });
  }

  // --- Sidebar collapse toggle --------------------------------------
  // The "Filters" button drives the <nldd-sidebar-section>'s own sheet.
  // The section renders the sidebar as a sticky aside on lg and collapses
  // it to a left sheet when narrower; toggle() opens/closes that sheet.
  function setupSidebarToggle() {
    document.addEventListener("click", (e) => {
      const path = e.composedPath();
      const btn = path.find(
        (el) => el instanceof Element && el.id === "nldd-sidebar-toggle",
      );
      if (!btn) return;
      const section = document.querySelector("nldd-sidebar-section");
      if (section && typeof section.toggle === "function") {
        section.toggle();
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
    const app = document.body;
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
    setupClearAllFilters();
    setupOrgQuickOptions();
    setupSearchSuggestionClicks();
    setupSidebarToggle();
    setupFilterOptionsModal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
