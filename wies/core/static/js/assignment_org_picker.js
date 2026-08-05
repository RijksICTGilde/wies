/**
 * Organisation picker on the assignment form (OrgPickerWidget).
 *
 * The widget template renders only the hidden formset inputs (each carrying
 * data-org-name so the label survives a page load) and the button that opens
 * the picker sheet. Everything visible is built here, from one source: the
 * inputs. That way a fresh page, an inline-edit swap and an apply from the
 * sheet all end up in the same state.
 *
 * The sheet itself lives in assignment_org_tree.js and only reports back what
 * was picked, via the `wies:org-selection-applied` event.
 */
(function () {
  "use strict";

  var INPUTS_ID = "assignment-org-inputs";
  var SELECTIONS_ID = "assignment-org-selections";
  var SHEET_ID = "assignment-org-modal";
  var SHEET_CONTAINER_ID = "assignment-org-modal-container";
  var PREFIX = "org";

  function cell(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      el.setAttribute(k, attrs[k]);
    });
    return el;
  }

  function rowsFromInputs() {
    var container = document.getElementById(INPUTS_ID);
    if (!container) return [];
    var rows = [];
    container
      .querySelectorAll("input[name$='-organization']")
      .forEach(function (input) {
        rows.push({
          nodeId: input.value,
          label: input.dataset.orgName || input.value,
          role: input.dataset.orgRole || "INVOLVED",
        });
      });
    return rows;
  }

  function rebuildInputs(rows) {
    var container = document.getElementById(INPUTS_ID);
    if (!container) return;
    container.innerHTML = "";

    var management = [
      [PREFIX + "-TOTAL_FORMS", String(rows.length)],
      [PREFIX + "-INITIAL_FORMS", "0"],
      [PREFIX + "-MIN_NUM_FORMS", "1"],
      [PREFIX + "-MAX_NUM_FORMS", "1000"],
    ];
    management.forEach(function (pair) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = pair[0];
      input.value = pair[1];
      container.appendChild(input);
    });

    rows.forEach(function (row, i) {
      var orgInput = document.createElement("input");
      orgInput.type = "hidden";
      orgInput.name = PREFIX + "-" + i + "-organization";
      orgInput.value = row.nodeId;
      orgInput.dataset.orgId = row.nodeId;
      orgInput.dataset.orgName = row.label;
      orgInput.dataset.orgRole = row.role;
      container.appendChild(orgInput);

      var roleInput = document.createElement("input");
      roleInput.type = "hidden";
      roleInput.name = PREFIX + "-" + i + "-role";
      roleInput.value = row.role;
      container.appendChild(roleInput);
    });
  }

  function renderSelection(rows) {
    var container = document.getElementById(SELECTIONS_ID);
    if (!container) return;
    container.innerHTML = "";

    // Exactly one primary as long as there is a row: the backend expects it and
    // the first one picked is the honest default.
    if (
      rows.length > 0 &&
      !rows.some(function (row) {
        return row.role === "PRIMARY";
      })
    ) {
      rows[0].role = "PRIMARY";
    }

    rebuildInputs(rows);
    if (rows.length === 0) return;

    var list = cell("nldd-list", {
      variant: "box",
      "accessible-label": "Gekozen opdrachtgevers",
    });

    rows.forEach(function (row, index) {
      var item = cell("nldd-list-item", {});
      var isPrimary = row.role === "PRIMARY";

      // "Primair" hoort bij de naam, dus als tag in dezelfde cel — niet als
      // los besturingselement verderop in de regel.
      var textCell = cell("nldd-text-cell", {});
      var line = document.createElement("span");
      line.textContent = row.label + " ";
      if (isPrimary) {
        var tag = cell("nldd-tag", {
          size: "sm",
          color: "accent",
          text: "Primair",
        });
        line.appendChild(tag);
      }
      textCell.appendChild(line);
      item.appendChild(textCell);

      item.appendChild(cell("nldd-spacer-cell", { size: "8" }));

      var menuCell = cell("nldd-cell", {});
      var trigger = cell("nldd-icon-button", {
        icon: "more",
        size: "sm",
        "tooltip-timing": "never",
        text: "Acties voor " + row.label,
      });
      // Slotted into the button rather than anchored by id: the button then
      // owns the anchoring and the open/close toggle itself.
      var menu = cell("nldd-menu", {
        slot: "popup",
        placement: "bottom-end",
      });
      if (!isPrimary) {
        var makePrimary = cell("nldd-menu-item", {
          text: "Maak primaire opdrachtgever",
          icon: "primary",
        });
        makePrimary.addEventListener("select", function () {
          rows.forEach(function (r) {
            r.role = r.nodeId === row.nodeId ? "PRIMARY" : "INVOLVED";
          });
          renderSelection(rows);
        });
        menu.appendChild(makePrimary);
        menu.appendChild(cell("nldd-menu-divider", {}));
      }
      var remove = cell("nldd-menu-item", {
        text: "Verwijder opdrachtgever",
        icon: "delete",
        destructive: "",
      });
      remove.addEventListener("select", function () {
        renderSelection(
          rows.filter(function (r) {
            return r.nodeId !== row.nodeId;
          }),
        );
      });
      menu.appendChild(remove);
      trigger.appendChild(menu);
      menuCell.appendChild(trigger);
      item.appendChild(menuCell);

      list.appendChild(item);
    });

    container.appendChild(list);
    // De ruimte tussen de lijst en de knop eronder hoort bij de lijst: staat hij
    // in de template, dan blijft er een gat van 12px onder het label zolang er
    // niets gekozen is. Hier wordt hij mee opgeruimd door de innerHTML-reset.
    container.appendChild(cell("nldd-spacer", { size: "12", direction: "vertical" }));
  }

  function renderFromInputs() {
    if (!document.getElementById(INPUTS_ID)) return;
    renderSelection(rowsFromInputs());
  }

  /** The trigger's htmx:configRequest adds what /client-modal needs: the orgs to
   *  pre-check, and count_mode=none so the endpoint returns the picker sheet
   *  (and no placement counts). Idempotent — runs on page load and after every
   *  swap, wiring the button exactly once. */
  function wireTriggerButton() {
    var button = document.getElementById("assignment-org-trigger-btn");
    if (!button || button.__wiesOrgPickerWired) return;
    button.__wiesOrgPickerWired = true;
    button.addEventListener("htmx:configRequest", function (e) {
      var orgIds = [];
      document
        .querySelectorAll("#" + INPUTS_ID + " input[data-org-id]")
        .forEach(function (input) {
          if (input.dataset.orgId) orgIds.push(input.dataset.orgId);
        });
      e.detail.parameters["count_mode"] = "none";
      if (orgIds.length) e.detail.parameters["org"] = orgIds;
    });
  }

  document.addEventListener("wies:org-selection-applied", function (e) {
    // Keep the role of an organisation that was already on the assignment: the
    // sheet knows nothing about primary/involved.
    var existingRoles = {};
    rowsFromInputs().forEach(function (row) {
      existingRoles[row.nodeId] = row.role;
    });
    var isFirst = true;
    var rows = (e.detail.rows || []).map(function (row) {
      var result = {
        nodeId: row.nodeId,
        label: row.label,
        role: existingRoles[row.nodeId] || (isFirst ? "PRIMARY" : "INVOLVED"),
      };
      isFirst = false;
      return result;
    });
    renderSelection(rows);
  });

  /** The sheet is fetched on demand, so it only exists after the swap. Wait for
   *  the element to upgrade and render before show(), or the call no-ops. */
  function openSheet() {
    var sheet = document.getElementById(SHEET_ID);
    if (!sheet) return;
    // Zit de picker in een ander sheet (de opdracht-invoeren/-bewerken sheet),
    // dan slikt de backdrop van dat buitenste sheet de open-klik in als
    // light-dismiss en flitst de picker dicht. Hijs hem naar body zodat de
    // modale dialogs niet stapelen. Op de full-page geen wrapper: no-op.
    if (sheet.closest("nldd-sheet") && sheet.parentElement !== document.body) {
      document.body.appendChild(sheet);
    }
    var show = function () {
      if (typeof sheet.show === "function") sheet.show();
    };
    if (
      sheet.updateComplete &&
      typeof sheet.updateComplete.then === "function"
    ) {
      sheet.updateComplete.then(show);
    } else {
      customElements.whenDefined("nldd-sheet").then(show);
    }
  }

  document.body.addEventListener("htmx:afterSettle", function (e) {
    var target = e.detail && e.detail.target;
    if (target && target.id === SHEET_CONTAINER_ID) {
      openSheet();
      return;
    }
    // The widget can arrive as part of an inline-edit partial, so re-wire the
    // trigger and rebuild the visible list from the newly inserted inputs.
    wireTriggerButton();
    renderFromInputs();
  });

  // Clear the sheet once it closes, so opening it again fetches a fresh tree
  // instead of reviving a stale one. Een gehesen sheet (nested case) zit niet
  // meer in de mount, dus die verwijderen we los.
  document.addEventListener(
    "close",
    function (e) {
      var sheet = e.composedPath().find(function (el) {
        return el instanceof Element && el.id === SHEET_ID;
      });
      if (!sheet) return;
      if (sheet.parentElement === document.body) {
        sheet.remove();
      } else {
        var container = document.getElementById(SHEET_CONTAINER_ID);
        if (container) container.innerHTML = "";
      }
    },
    true,
  );

  wireTriggerButton();
  renderFromInputs();
})();
