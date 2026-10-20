// Organisation picker on the assignment form. The visible list is built from
// the hidden formset inputs, so every entry point lands in the same state.
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

    // The backend expects exactly one primary.
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
      // Slotted, not anchored by id: the button then owns the toggle itself.
      var menu = cell("nldd-menu", {
        slot: "popup",
        placement: "bottom-end",
      });
      // No per-item listener: the delegated `select` below serves
      // server-rendered and locally built chips alike.
      if (!isPrimary) {
        menu.appendChild(
          cell("nldd-menu-item", {
            text: "Maak primaire opdrachtgever",
            icon: "primary",
            "data-org-picker-action": "make-primary",
            "data-node-id": row.nodeId,
          }),
        );
        menu.appendChild(cell("nldd-menu-divider", {}));
      }
      menu.appendChild(
        cell("nldd-menu-item", {
          text: "Verwijder opdrachtgever",
          icon: "delete",
          destructive: "",
          "data-org-picker-action": "remove",
          "data-node-id": row.nodeId,
        }),
      );
      trigger.appendChild(menu);
      menuCell.appendChild(trigger);
      item.appendChild(menuCell);

      list.appendChild(item);
    });

    container.appendChild(list);
    // In the list, not the template: the gap must go when nothing is picked.
    container.appendChild(
      cell("nldd-spacer", { size: "12", direction: "vertical" }),
    );
  }

  function renderFromInputs() {
    if (!document.getElementById(INPUTS_ID)) return;
    // Only when missing: the server already renders the chip list.
    var container = document.getElementById(SELECTIONS_ID);
    if (container && container.querySelector("nldd-list")) return;
    renderSelection(rowsFromInputs());
  }

  // count_mode=none: the picker does not need placement counts.
  function wireTriggerButton() {
    var button = document.getElementById("assignment-org-trigger-btn");
    if (!button || button.__wiesOrgPickerWired) return;
    button.__wiesOrgPickerWired = true;
    button.addEventListener("htmx:configRequest", function (e) {
      e.detail.parameters["count_mode"] = "none";
    });
  }

  // Rows come from the hidden inputs, not from a captured array.
  document.addEventListener("select", function (e) {
    var item = e.composedPath().find(function (el) {
      return el instanceof Element && el.dataset && el.dataset.orgPickerAction;
    });
    if (!item) return;
    var action = item.dataset.orgPickerAction;
    var nodeId = item.dataset.nodeId;
    var rows = rowsFromInputs();
    if (action === "make-primary") {
      rows.forEach(function (r) {
        r.role = r.nodeId === nodeId ? "PRIMARY" : "INVOLVED";
      });
    } else if (action === "remove") {
      rows = rows.filter(function (r) {
        return r.nodeId !== nodeId;
      });
    } else {
      return;
    }
    renderSelection(rows);
  });

  document.addEventListener("wies:org-selection-applied", function (e) {
    // The sheet adds rather than replaces and knows nothing about roles.
    var rows = rowsFromInputs();
    var seen = {};
    rows.forEach(function (row) {
      seen[row.nodeId] = true;
    });
    (e.detail.rows || []).forEach(function (row) {
      if (seen[row.nodeId]) return;
      seen[row.nodeId] = true;
      rows.push({ nodeId: row.nodeId, label: row.label, role: "INVOLVED" });
    });
    renderSelection(rows);
  });

  // show() no-ops until the freshly swapped element has upgraded and rendered.
  function openSheet() {
    var sheet = document.getElementById(SHEET_ID);
    if (!sheet) return;
    // Inside another sheet the outer backdrop takes the opening click as a
    // light-dismiss and the picker flashes shut; hoisting avoids the stacking.
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
    wireTriggerButton();
    renderFromInputs();
  });

  // Clear on close, so reopening fetches a fresh tree. A hoisted sheet is no
  // longer in the mount, hence the two branches.
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
