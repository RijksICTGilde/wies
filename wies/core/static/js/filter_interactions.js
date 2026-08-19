// Glue for the list filters. No hx-* click forwarding: htmx 2 wires custom
// elements itself, so a bridge duplicated every request.

(function () {
  "use strict";

  const NDD_TEXT = "nldd-text-field, nldd-date-field";
  const NDD_SEARCH = "nldd-search-field[data-wies-search-input]";

  function dispatchFormChange(form) {
    if (!form) return;
    const sentinel = form.querySelector("[data-filter-input]");
    (sentinel || form).dispatchEvent(new Event("change", { bubbles: true }));
  }

  // The nldd-checkbox in a filter row is decorative; a hidden native checkbox
  // behind the list submits.

  // By group id: the groups sit flat, so an unscoped query hit the first slot.
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

  function syncRowCheckbox(row) {
    const box = row.querySelector("nldd-checkbox");
    if (box) box.checked = !!row.checked;
  }

  function setRowChecked(row, checked) {
    if (!row) return;
    row.checked = checked;
    syncRowCheckbox(row);
  }

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

  // Form-associated: the value submits natively, only the re-filter needs a nudge.
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

  function suggestionMenu() {
    return document.getElementById("search-suggestions");
  }

  // Driven by a MutationObserver, not the htmx promise: that resolves before
  // the swap settles, leaving the menu one response behind.
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

  // anchorElement, not the `anchor` attribute: that also makes the field a
  // toggle, so clicking into it would open an empty menu.
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
    // Blur the inner input too, or the dropdown reopens on focus.
    try {
      el.blur();
      el.shadowRoot?.querySelector("input")?.blur();
    } catch (_) {}
  }

  function attachSearchField(el) {
    if (el.__nddSearchAttached) return;
    el.__nddSearchAttached = true;
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

    // Capture phase: the field handles Enter on its inner input, so a bubbling
    // listener runs too late.
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

    el.addEventListener("search", (e) => {
      commitSearch(el, (e.detail?.value ?? el.value ?? "").trim());
    });
    el.addEventListener("change", (e) => {
      const v = (e.detail?.value ?? el.value ?? "").trim();
      if (!v) commitSearch(el, "");
    });
  }

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

  // The status cards (Bezetting summary) live in #results, not the filter form,
  // but their hidden checkboxes carry data-filter-input so hx-include submits
  // them. Toggling one flips the checkbox + aria-pressed and re-filters.
  function statusCardInput(card) {
    return card.querySelector('input[name="status"]');
  }

  function setStatusCard(card, active) {
    const input = statusCardInput(card);
    if (input) {
      input.checked = active;
      if (active) input.setAttribute("checked", "");
      else input.removeAttribute("checked");
    }
    card.setAttribute("aria-pressed", active ? "true" : "false");
  }

  function setupStatusCards() {
    document.addEventListener("click", (e) => {
      const card = e
        .composedPath()
        .find(
          (el) => el instanceof Element && el.hasAttribute?.("data-status-card"),
        );
      if (!card) return;
      const input = statusCardInput(card);
      setStatusCard(card, input ? !input.checked : true);
      dispatchFormChange(document.getElementById("filter-form"));
    });
  }

  function removeFilter(name, value) {
    const form = document.getElementById("filter-form");
    if (!form) return;

    // Status cards sit outside the form (in #results); untick by card, not input.
    if (name === "status") {
      const card = document.querySelector(
        `[data-status-card][data-status="${CSS.escape(value)}"]`,
      );
      if (card) setStatusCard(card, false);
      dispatchFormChange(form);
      return;
    }

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

    // nldd-date-field commits a programmatic value a render later, in updated().
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

    // "labels" repeats per category, so several groups share the name.
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

  // nldd-token's "dismiss" is composed, so it reaches document.
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

  // The sidebar's org options each carry their own param, bypassing the modal.
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

  // Ticking in the "Meer..." sheet is deferred: closing discards it.
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

    function updateApplyLabel(sheet) {
      const button = sheet.querySelector("#filter-options-apply-btn");
      if (!button) return;
      const count = checkedValues(sheet).length;
      let text = "Pas toe";
      if (count === 1) text = "Pas filter toe";
      else if (count > 1) text = `Pas ${count} filters toe`;
      button.setAttribute("text", text);
    }

    // show() no-ops while the shadow <dialog> is unrendered, as right after a swap.
    function openWhenReady(sheet, attempt) {
      if (!sheet) return;
      const tryShow = () => {
        if (
          typeof sheet.show === "function" &&
          sheet.shadowRoot?.querySelector("dialog")
        ) {
          // Only a child sheet sometimes: the sidebar is a sheet when narrow.
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
        if (sheet) updateApplyLabel(sheet);
      }
    });

    // Empty on close, so reopening fetches a fresh list.
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

    // A row toggle here does not submit; that is the CTA's job.
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
        // The sheet can pick values the top-N sidebar has no row for, so
        // rebuild from the selection rather than from the rows.
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

    // Status cards live in #results, outside the form; reset them separately.
    document
      .querySelectorAll("[data-status-card]")
      .forEach((card) => setStatusCard(card, false));

    form
      .querySelectorAll(
        "[data-filter-input]:checked, [data-filter-input][checked]",
      )
      .forEach((input) => {
        input.checked = false;
        input.removeAttribute("checked");
      });
    form.querySelectorAll("nldd-list-item[checked]").forEach((row) => {
      setRowChecked(row, false);
    });

    // Date fields commit asynchronously in updated(), see removeFilter.
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

  // The OOB swap of #filter-panel makes nldd-page reset scrollTop.
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

  // The sidebar scroller sits in a shadow root findScroller cannot reach; the
  // fallback covers the narrow-screen sheet.
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
      // Twice: the aside's reset can land a frame after the settle.
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
    setupStatusCards();
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
