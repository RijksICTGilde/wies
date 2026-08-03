// Filter interactions (opdrachten/plaatsingen/gebruikers list filters).
// ----------------------------------------------------------------------------
// Filter inputs carry their own name + data-filter-input and are form-
// associated (or plain), so hx-include submits their values natively. This
// module only covers the interaction glue the browser can't do for us:
//   1. Nudges a re-filter (synthetic `change` on a [data-filter-input]
//      element) when an nldd-* field or filter checkbox changes, so
//      hx-trigger="change from:[data-filter-input]" fires.
//   2. nldd-search-field → #search-hidden with debounce + suggestions.
//   3. MutationObserver picks up NDD elements added after HTMX swaps.
//   4. Dismiss handler voor nldd-token chips → verwijdert filter.
//   5. "Wis alle filters".
//   6. Opdrachtgever quick-options.
//   7. "Meer"-modal: schrijft niet-inline picks in een overflow-slot.
//
// The sidebar toggle that used to live here is now sidebar_toggle.js. The
// nldd-* hx-* click forwarding is gone entirely: htmx 2 wires custom elements
// itself, so the bridge only produced a second, duplicate request.
// ----------------------------------------------------------------------------

(function () {
  "use strict";

  const NDD_TEXT = "nldd-text-field, nldd-date-field";
  const NDD_SEARCH = "nldd-search-field";

  // Filter checkboxes carry their own `name` + `data-filter-input`, so the
  // browser submits them via hx-include and htmx's own
  // hx-trigger="change from:[data-filter-input]" re-runs the filter — no glue
  // needed here. Custom elements (nldd-text-field/-search-field) below aren't
  // seen by that trigger, so they get a nudge.

  function dispatchFormChange(form) {
    if (!form) return;
    // Triggert hx-trigger="change from:[data-filter-input]" op de form.
    const sentinel = form.querySelector("[data-filter-input]");
    (sentinel || form).dispatchEvent(new Event("change", { bubbles: true }));
  }

  // A filter row is an nldd-list-item[checkbox]: the row carries role and
  // state, the nldd-checkbox inside it is decorative, and a hidden native
  // checkbox behind the list is what actually submits. These three helpers
  // keep them in step.
  /** Look the slot up by group id, not by position. The groups sit flat in the
   *  form, so a plain [data-hidden-inputs] query handed EVERY group the first
   *  slot in the form — only the topmost filter still submitted. */
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

  // A row toggle writes through to the hidden input that submits.
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

  // Both are form-associated, so their value reaches the request
  // natively (no hidden-input mirror needed). We only have to nudge the form
  // to re-run the filter when the value changes, since the form's hx-trigger
  // listens for `change` from [data-filter-input] elements.
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

  // nldd-search-field fires: `input` (typing), `search` (Enter / search
  // button), `change` (blur). We show live suggestions while typing and
  // commit the search (write hidden -> run filter, hide suggestions, blur)
  // on `search`. Committing via a suggestion click routes through here too.
  function suggestionMenu() {
    return document.getElementById("search-suggestions");
  }

  /** Opens the menu when it holds items, closes it when it doesn't.
   *  Driven by a MutationObserver on the menu, not by the htmx promise: that
   *  promise resolves before the swap settles, so syncing on it left the menu
   *  one response behind — and an emptied menu stayed open showing nldd-menu's
   *  "Geen opties beschikbaar". Also stays closed once the field is empty, so a
   *  late response for an already-cleared term can't reopen it. */
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

  /** Anchor the menu by element reference instead of by id.
   *
   * With the `anchor` ATTRIBUTE nldd-menu also treats that element as a
   * toggle: it listens on document click and opens itself whenever the click
   * path contains the anchor. Right for a button-anchored menu, wrong here —
   * clicking into the search field would open an empty menu showing "Geen
   * opties beschikbaar". Setting `anchorElement` gives the same Floating UI
   * positioning but skips the toggle, leaving open/close entirely to us. */
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
    // Wire the menu up front: the toggle would otherwise fire on the very
    // first click into the field, before anything has been typed.
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

    // The menu is variant="listbox", so it never takes focus. Forward the
    // navigation keys to it, the same way nldd-combo-box drives its own menu.
    // Capture phase: the search field handles Enter on its own inner input, so
    // a bubbling listener would run too late to claim it for the menu.
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
  // typed term — you searched for a shorthand, you get the organisation.
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

    // Date filter: the nldd-date-field submits its own value, so clearing that
    // value IS removing the filter. Programmatic value sets commit their form
    // value in the component's updated() — a render later — so wait for
    // updateComplete before serialising, or the request still carries the old
    // date and the OOB swap puts it right back.
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

    // Multi-select: uncheck the submitting input and mirror it back onto the
    // row. "labels" repeats per category, so several groups share
    // data-name="labels" — search ALL of them, not just the first.
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

    // Org filters (modal-managed): verwijder hidden input direct.
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

  // nldd-token "dismiss" event is composed:true (volgens NDD code)
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
  // (org / org_self / org_type). Ticking one writes/removes a hidden input
  // in #org-filter-inputs and re-runs the filter — no modal needed.
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
  // writes the selection back to the sidebar group and re-runs the filter.
  // Closing (title bar / Escape) discards the changes.
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

    /** Same CTA wording as the opdrachtgever-sheet: the button says what it is
     *  about to apply, so no separate counter is needed. With nothing ticked
     *  there is no filter to name, hence the neutral wording. */
    function updateApplyLabel(sheet) {
      const button = sheet.querySelector("#filter-options-apply-btn");
      if (!button) return;
      const count = checkedValues(sheet).length;
      let text = "Pas toe";
      if (count === 1) text = "Pas filter toe";
      else if (count > 1) text = `Pas ${count} filters toe`;
      button.setAttribute("text", text);
    }

    // Open the sheet once htmx swaps it in. It is a Lit component: right after
    // the swap its shadow <dialog> may not exist yet, so show() would no-op.
    // Wait for the element to upgrade + finish its first render, fall back to rAF.
    function openWhenReady(sheet, attempt) {
      if (!sheet) return;
      const tryShow = () => {
        if (
          typeof sheet.show === "function" &&
          sheet.shadowRoot?.querySelector("dialog")
        ) {
          // Terugknop alleen als deze sheet vanuit een andere sheet opent (de
          // filterzijbalk is op een smal scherm zelf een sheet, op een breed
          // scherm een paneel).
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
        // The server pre-ticks what is already filtered, so the CTA has to
        // count before anything is clicked.
        if (sheet) updateApplyLabel(sheet);
      }
    });

    // Empty the mount point once the sheet is closed, so opening it again
    // fetches a fresh list instead of reviving a stale one.
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

    // A row toggle inside the sheet mirrors onto its decorative checkbox and
    // updates the CTA. Nothing submits yet — that is what the CTA is for.
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
        // The sidebar only lists the top-N, so the sheet can pick values that
        // have no row. Rebuild the submitting inputs from the sheet selection
        // and mirror the ones that do have a row back onto it.
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
