// Filter interactions (opdrachten/plaatsingen/gebruikers list filters).
//
// Filter inputs carry their own name + data-filter-input, so hx-include submits
// their values natively. This module only covers the glue the browser cannot
// do: nudging a re-filter with a synthetic `change` so
// hx-trigger="change from:[data-filter-input]" fires, the search field with its
// suggestions, token dismissal, "Wis alle filters", opdrachtgever quick options
// and the "Meer" modal. A MutationObserver picks up nldd elements added by
// HTMX swaps.
//
// There is deliberately no hx-* click forwarding for nldd elements: htmx 2
// wires custom elements itself, so a bridge only produced a duplicate request.

(function () {
  "use strict";

  const NDD_TEXT = "nldd-text-field, nldd-date-field";
  // Scoped so attachSearchField skips the modal/org/client search fields, which
  // must not drive the global `zoek` query.
  const NDD_SEARCH = "nldd-search-field[data-wies-search-input]";

  function dispatchFormChange(form) {
    if (!form) return;
    // Fires the form's hx-trigger="change from:[data-filter-input]".
    const sentinel = form.querySelector("[data-filter-input]");
    (sentinel || form).dispatchEvent(new Event("change", { bubbles: true }));
  }

  // A filter row is an nldd-list-item[checkbox]: the row carries role and state,
  // the nldd-checkbox inside it is decorative, and a hidden native checkbox
  // behind the list is what submits. The helpers below keep them in step.

  /** Returns the hidden-input slot of a group, looked up by group id. The groups
   *  sit flat in the form, so a plain [data-hidden-inputs] query handed every
   *  group the first slot and only the topmost filter still submitted. */
  function inputSlot(group) {
    const groupId = group.dataset.groupId;
    const form = group.closest("form");
    if (!form || !groupId) return null;
    return form.querySelector(`[data-hidden-inputs="${CSS.escape(groupId)}"]`);
  }

  function inputFor(group, value) {
    const slot = inputSlot(group);
    if (!slot) return null;
    return Array.from(slot.querySelectorAll("input")).find(
      (el) => el.value === value,
    );
  }

  function rowFor(group, value) {
    return group.querySelector(
      `nldd-list-item[data-value="${CSS.escape(value)}"]`,
    );
  }

  /** Mirrors the row's state onto its decorative nldd-checkbox. */
  function syncRowCheckbox(row) {
    const box = row.querySelector("nldd-checkbox");
    if (box) box.checked = !!row.checked;
  }

  function setRowChecked(row, checked) {
    if (!row) return;
    row.checked = checked;
    syncRowCheckbox(row);
  }

  /** Writes a row toggle through to the hidden input that submits. */
  function setupFilterRows() {
    document.addEventListener("change", (e) => {
      const row = e.target;
      if (
        !(row instanceof Element) ||
        row.localName !== "nldd-list-item" ||
        !row.dataset.value ||
        row.dataset.orgParam
      ) {
        return;
      }
      const group = row.closest("[data-wies-fieldset]");
      if (!group) return;
      syncRowCheckbox(row);
      const input = inputFor(group, row.dataset.value);
      if (input) {
        input.checked = !!row.checked;
        if (row.checked) input.setAttribute("checked", "");
        else input.removeAttribute("checked");
      }
      dispatchFormChange(document.getElementById("filter-form"));
    });
  }

  // Both are form-associated, so their value reaches the request natively; only
  // the re-filter needs a nudge, since the form's hx-trigger listens for
  // `change` from [data-filter-input] elements.
  function attachTextField(el) {
    if (el.__nddBridgeAttached) return;
    el.__nddBridgeAttached = true;
    if (!el.getAttribute("name")) return;
    const onChange = () => {
      const form = el.closest("form");
      if (form) dispatchFormChange(form);
    };
    el.addEventListener("change", onChange);
    el.addEventListener("input", onChange);
  }

  // nldd-search-field fires `input` (typing), `search` (Enter / search button)
  // and `change` (blur): suggestions appear while typing, `search` commits.
  function suggestionMenu() {
    return document.getElementById("search-suggestions");
  }

  /** Opens the menu when it holds items, closes it when it does not. Driven by a
   *  MutationObserver on the menu, not by the htmx promise: that promise
   *  resolves before the swap settles, leaving the menu one response behind.
   *  Stays closed once the field is empty, so a late response for an
   *  already-cleared term cannot reopen it. */
  function syncSuggestionMenu() {
    const menu = suggestionMenu();
    if (!menu) return;
    const field = document.querySelector("[data-wies-search-input]");
    const hasTerm = ((field && field.value) || "").trim() !== "";
    const hasItems = menu.querySelector("nldd-menu-item") !== null;
    const open = menu.matches(":popover-open");
    if (hasItems && hasTerm && !open) menu.showPopover?.();
    else if ((!hasItems || !hasTerm) && open) menu.hidePopover?.();
  }

  function observeSuggestionMenu() {
    const menu = suggestionMenu();
    if (!menu || menu.__wiesObserved) return;
    menu.__wiesObserved = true;
    new MutationObserver(syncSuggestionMenu).observe(menu, { childList: true });
  }

  /** Anchors the suggestion menu by element reference instead of by id. With the
   *  `anchor` attribute nldd-menu also treats that element as a toggle and opens
   *  itself on any click containing the anchor, so clicking into the search
   *  field would open an empty menu. `anchorElement` gives the same positioning
   *  without the toggle, leaving open/close to us. */
  function anchorSuggestionMenu() {
    const menu = suggestionMenu();
    const field = document.querySelector("[data-wies-search-input]");
    if (!menu || !field || menu.anchorElement) return;
    menu.anchorElement = field;
    menu.removeAttribute("anchor");
  }

  function hideSuggestions() {
    const menu = suggestionMenu();
    if (!menu) return;
    if (menu.matches(":popover-open")) menu.hidePopover?.();
    menu.innerHTML = "";
  }

  function commitSearch(el, value) {
    const hidden = document.getElementById("search-hidden");
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
    // Wire the menu up front: the toggle would otherwise fire on the first
    // click into the field, before anything has been typed.
    anchorSuggestionMenu();
    observeSuggestionMenu();
    let timer = null;

    el.addEventListener("input", (e) => {
      const term = (e.detail?.value ?? el.value ?? "").trim();
      clearTimeout(timer);
      if (!term) {
        hideSuggestions();
        return;
      }
      timer = setTimeout(() => {
        const menu = suggestionMenu();
        if (!menu || !window.htmx) return;
        window.htmx.ajax(
          "GET",
          `/zoek-suggesties/?zoek=${encodeURIComponent(term)}`,
          { target: "#search-suggestions", swap: "innerHTML" },
        );
      }, 250);
    });

    // The menu is variant="listbox" and never takes focus, so navigation keys
    // are forwarded to it. Capture phase: the search field handles Enter on its
    // own inner input, so a bubbling listener would run too late.
    el.addEventListener(
      "keydown",
      (e) => {
        const menu = suggestionMenu();
        if (!menu || !menu.matches(":popover-open")) return;
        if (e.key === "ArrowDown") {
          e.preventDefault();
          menu.moveHighlight("next");
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          menu.moveHighlight("prev");
        } else if (e.key === "Escape") {
          e.preventDefault();
          hideSuggestions();
        } else if (e.key === "Enter") {
          const highlighted = menu.getHighlighted?.();
          if (highlighted) {
            e.preventDefault();
            e.stopPropagation();
            highlighted.select();
          }
        }
      },
      true,
    );

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

  // An org suggestion applies the abbreviation as an org filter and clears the
  // typed term: you searched for a shorthand, you get the organisation.
  function setupSearchSuggestionSelect() {
    document.addEventListener("select", (e) => {
      const item = e
        .composedPath()
        .find(
          (x) =>
            x instanceof Element &&
            x.localName === "nldd-menu-item" &&
            x.dataset.orgId,
        );
      if (!item) return;
      const form = document.getElementById("filter-form");
      const container = document.getElementById("org-filter-inputs");
      const orgId = item.dataset.orgId;
      if (
        container &&
        !container.querySelector(
          `input[name="org"][value="${CSS.escape(orgId)}"]`,
        )
      ) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "org";
        input.value = orgId;
        input.setAttribute("data-filter-input", "");
        input.setAttribute("data-label", item.dataset.orgLabel || "");
        container.appendChild(input);
      }
      const searchField = document.querySelector("[data-wies-search-input]");
      if (searchField) {
        try {
          searchField.value = "";
        } catch (_) {}
      }
      const hidden = document.getElementById("search-hidden");
      if (hidden) hidden.value = "";
      hideSuggestions();
      if (form) dispatchFormChange(form);
    });
  }

  function removeFilter(name, value) {
    const form = document.getElementById("filter-form");
    if (!form) return;

    if (name === "zoek") {
      const hidden = document.getElementById("search-hidden");
      const searchField = document.querySelector("[data-wies-search-input]");
      if (hidden) hidden.value = "";
      if (searchField) {
        try {
          searchField.value = "";
        } catch (_) {}
      }
      dispatchFormChange(form);
      return;
    }

    // The nldd-date-field submits its own value, so clearing it removes the
    // filter. A programmatic set commits its form value a render later, in
    // updated(), so wait for updateComplete before serialising or the request
    // still carries the old date and the OOB swap puts it back.
    const dateField = form.querySelector(
      `nldd-date-field[name="${CSS.escape(name)}"]`,
    );
    if (dateField) {
      try {
        dateField.value = "";
      } catch (_) {}
      Promise.resolve(dateField.updateComplete).then(() =>
        dispatchFormChange(form),
      );
      return;
    }

    // Multi-select: uncheck the submitting input and mirror it onto the row.
    // "labels" repeats per category, so several groups share
    // data-name="labels" and all of them have to be searched.
    if (value !== null) {
      const groups = form.querySelectorAll(
        `[data-wies-fieldset][data-name="${CSS.escape(name)}"]`,
      );
      for (const group of groups) {
        const input = inputFor(group, value);
        if (input) {
          input.checked = false;
          input.removeAttribute("checked");
          setRowChecked(rowFor(group, value), false);
          dispatchFormChange(form);
          return;
        }
      }
    }

    // Org filters (modal-managed): remove the hidden input directly.
    const orgContainer = document.getElementById("org-filter-inputs");
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

  // The nldd-token "dismiss" event is composed, so it can be caught here.
  function setupTokenDismiss() {
    document.addEventListener("dismiss", (e) => {
      const path = e.composedPath();
      const token = path.find(
        (el) =>
          el instanceof Element && el.tagName?.toLowerCase() === "nldd-token",
      );
      if (!token) return;
      if (token.dataset.wiesDismiss !== "filter") return;
      removeFilter(token.dataset.filterName, token.dataset.filterValue || null);
    });
  }

  // The top-3 org quick options in the sidebar each carry their own param
  // (org / org_self / org_type), so ticking one writes or removes a hidden
  // input in #org-filter-inputs and re-runs the filter without the modal.
  function setupOrgQuickOptions() {
    document.addEventListener("change", (e) => {
      const row = e.target;
      if (
        !(row instanceof Element) ||
        row.localName !== "nldd-list-item" ||
        !row.dataset.orgParam
      ) {
        return;
      }
      syncRowCheckbox(row);
      const form = document.getElementById("filter-form");
      const container = document.getElementById("org-filter-inputs");
      if (!form || !container) return;
      const param = row.dataset.orgParam;
      const value = row.dataset.value;
      const cb = { checked: row.checked, dataset: row.dataset };
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

  // A sidebar group's "Meer..." row opens filter_options_modal.html into
  // #filter-options-modal-container. Ticking there is deferred: only the CTA
  // writes the selection back and re-runs the filter, closing discards it.
  function setupFilterOptionsModal() {
    const SHEET_ID = "filter-options-modal";
    const container = document.getElementById("filter-options-modal-container");

    function currentSheet() {
      return document.getElementById(SHEET_ID);
    }

    function optionRows(sheet) {
      return [...sheet.querySelectorAll("nldd-list-item[data-value]")];
    }

    function checkedValues(sheet) {
      return optionRows(sheet)
        .filter((row) => row.checked)
        .map((row) => row.dataset.value);
    }

    /** Updates the CTA label to name what it is about to apply, so no separate
     *  counter is needed. Neutral wording when nothing is ticked. */
    function updateApplyLabel(sheet) {
      const button = sheet.querySelector("#filter-options-apply-btn");
      if (!button) return;
      const count = checkedValues(sheet).length;
      let text = "Pas toe";
      if (count === 1) text = "Pas filter toe";
      else if (count > 1) text = `Pas ${count} filters toe`;
      button.setAttribute("text", text);
    }

    // Opens the sheet once htmx swaps it in. It is a Lit component whose shadow
    // <dialog> may not exist right after the swap, so show() would no-op: wait
    // for the first render, falling back to rAF.
    function openWhenReady(sheet, attempt) {
      if (!sheet) return;
      const tryShow = () => {
        if (
          typeof sheet.show === "function" &&
          sheet.shadowRoot?.querySelector("dialog")
        ) {
          // Back button only when this sheet opens from another sheet: on a
          // narrow screen the filter sidebar is itself a sheet, on a wide
          // screen a panel.
          if (typeof window.syncSheetBackButton === "function") {
            window.syncSheetBackButton(sheet);
          }
          sheet.show();
        } else if ((attempt || 0) < 20) {
          requestAnimationFrame(() => openWhenReady(sheet, (attempt || 0) + 1));
        }
      };
      if (
        sheet.updateComplete &&
        typeof sheet.updateComplete.then === "function"
      ) {
        sheet.updateComplete.then(tryShow);
      } else {
        tryShow();
      }
    }

    document.body.addEventListener("htmx:afterSwap", (e) => {
      const t = e.target;
      if (
        t &&
        (t.id === "filter-options-modal-container" ||
          (t.closest && t.closest("#filter-options-modal-container")))
      ) {
        const sheet = currentSheet();
        openWhenReady(sheet, 0);
        // The server pre-ticks what is already filtered, so the CTA counts
        // before anything is clicked.
        if (sheet) updateApplyLabel(sheet);
      }
    });

    // Empty the mount point on close, so reopening fetches a fresh list.
    document.addEventListener(
      "close",
      (e) => {
        const sheet = e
          .composedPath()
          .find((el) => el instanceof Element && el.id === SHEET_ID);
        if (!sheet) return;
        if (container) container.innerHTML = "";
      },
      true,
    );

    // A row toggle inside the sheet only mirrors onto its decorative checkbox
    // and updates the CTA; submitting is the CTA's job.
    document.addEventListener("change", (e) => {
      const row = e.target;
      if (!(row instanceof Element) || row.localName !== "nldd-list-item") {
        return;
      }
      const sheet = row.closest("#" + SHEET_ID);
      if (!sheet) return;
      syncRowCheckbox(row);
      updateApplyLabel(sheet);
    });

    document.addEventListener("click", (e) => {
      const applyBtn = e
        .composedPath()
        .find(
          (el) => el instanceof Element && el.id === "filter-options-apply-btn",
        );
      if (!applyBtn) return;

      const sheet = currentSheet();
      if (!sheet) return;
      const groupId = sheet.getAttribute("data-group-id");
      const values = checkedValues(sheet);

      const group = document.querySelector(
        `[data-wies-fieldset][data-group-id="${CSS.escape(groupId)}"]`,
      );
      const form = document.getElementById("filter-form");
      if (group) {
        // The sidebar only lists the top-N, so the sheet can pick values with
        // no row: rebuild the submitting inputs from the sheet selection and
        // mirror the ones that do have a row back onto it.
        const slot = inputSlot(group);
        const name = group.dataset.name;
        if (slot && name) {
          slot.innerHTML = "";
          for (const v of values) {
            const input = document.createElement("input");
            input.type = "checkbox";
            input.name = name;
            input.value = v;
            input.checked = true;
            input.setAttribute("data-filter-input", "");
            slot.appendChild(input);
          }
        }
        group.querySelectorAll("nldd-list-item[data-value]").forEach((row) => {
          setRowChecked(row, values.includes(row.dataset.value));
        });
      }
      if (sheet.hide) sheet.hide();
      if (form) dispatchFormChange(form);
    });

    // Live search within the sheet.
    document.addEventListener("input", (e) => {
      const search = e
        .composedPath()
        .find(
          (el) => el instanceof Element && el.id === "filter-options-search",
        );
      if (!search) return;
      const term = (search.value || "").toLowerCase().trim();
      const sheet = currentSheet();
      if (!sheet) return;
      optionRows(sheet).forEach((row) => {
        const label = row.dataset.optionLabel || "";
        row.hidden = Boolean(term) && !label.includes(term);
      });
    });
  }

  function scan(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll(NDD_TEXT).forEach(attachTextField);
    root.querySelectorAll(NDD_SEARCH).forEach(attachSearchField);
  }

  /** Clears every filter type and re-runs the filter once. */
  function clearAllFilters() {
    const form = document.getElementById("filter-form");
    if (!form) return;

    const searchHidden = document.getElementById("search-hidden");
    if (searchHidden) searchHidden.value = "";
    const searchField = document.querySelector("[data-wies-search-input]");
    if (searchField) {
      try {
        searchField.value = "";
      } catch (_) {}
    }

    const orgContainer = document.getElementById("org-filter-inputs");
    if (orgContainer) orgContainer.innerHTML = "";

    form
      .querySelectorAll(
        "[data-filter-input]:checked, [data-filter-input][checked]",
      )
      .forEach((input) => {
        input.checked = false;
        input.removeAttribute("checked");
      });
    // Host reflects `checked`; aria-checked lives only on the shadow button.
    form.querySelectorAll("nldd-list-item[checked]").forEach((row) => {
      setRowChecked(row, false);
    });

    // Date fields commit their value asynchronously in updated(), so wait for
    // every updateComplete before the form change (see removeFilter).
    const dateFields = Array.from(form.querySelectorAll("nldd-date-field"));
    const pending = dateFields.map((field) => {
      try {
        field.value = "";
      } catch (_) {}
      return Promise.resolve(field.updateComplete);
    });
    Promise.all(pending).then(() => dispatchFormChange(form));
  }

  function setupClearAllFilters() {
    document.addEventListener("click", (e) => {
      const btn = e
        .composedPath()
        .find(
          (el) =>
            el instanceof Element &&
            el.hasAttribute?.("data-clear-all-filters"),
        );
      if (!btn) return;
      e.preventDefault();
      clearAllFilters();
    });
  }

  // A filter change replaces #filter-panel through an OOB swap, after which
  // nldd-page resets its scrollTop and the page jumps to the top.
  function findScroller(start) {
    let el = start;
    while (el && el !== document.body) {
      const style = getComputedStyle(el);
      if (
        /(auto|scroll)/.test(style.overflowY) &&
        el.scrollHeight > el.clientHeight
      ) {
        return el;
      }
      el = el.parentElement || el.getRootNode()?.host;
    }
    return document.scrollingElement || document.documentElement;
  }

  /** Returns the scroller of the filter sidebar. It is
   *  .sidebar-section__sidebar-box inside nldd-sidebar-section's shadow root,
   *  which findScroller cannot reach: it climbs the host chain while the
   *  scroller sits in an ancestor's shadow root. On a narrow screen the sidebar
   *  becomes a sheet with its own scroller, hence the findScroller fallback. */
  function filterSidebarScroller() {
    const section = document.querySelector("nldd-sidebar-section");
    const box = section?.shadowRoot?.querySelector(
      ".sidebar-section__sidebar-box",
    );
    if (box && box.scrollHeight > box.clientHeight) return box;
    const panel = document.getElementById("filter-panel");
    return panel ? findScroller(panel) : null;
  }

  function setupFilterScrollPreserve() {
    let saved = null;
    document.addEventListener("htmx:beforeSwap", (e) => {
      if (e.detail.target?.id !== "results") return;
      const scroller = filterSidebarScroller();
      if (!scroller) return;
      saved = { scroller: scroller, top: scroller.scrollTop };
    });
    function restore() {
      if (!saved) return;
      const { scroller, top } = saved;
      // The OOB swap of #filter-panel rebuilds the slotted content and the aside
      // resets its scrollTop to 0. Restore it again in the next frame, since
      // that reset can land asynchronously after the settle.
      scroller.scrollTop = top;
      requestAnimationFrame(() => {
        scroller.scrollTop = top;
        saved = null;
      });
    }
    document.addEventListener("htmx:afterSettle", restore);
  }

  function init() {
    const app = document.body;
    if (!app) return;

    scan(app);

    new MutationObserver((mutations) => {
      for (const m of mutations) {
        m.addedNodes.forEach((n) => {
          if (n.nodeType !== 1) return;
          if (n.matches?.(NDD_TEXT)) attachTextField(n);
          if (n.matches?.(NDD_SEARCH)) attachSearchField(n);
          scan(n);
        });
      }
    }).observe(app, { childList: true, subtree: true });

    setupTokenDismiss();
    setupClearAllFilters();
    setupFilterScrollPreserve();
    setupFilterRows();
    setupOrgQuickOptions();
    setupSearchSuggestionSelect();
    setupFilterOptionsModal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
