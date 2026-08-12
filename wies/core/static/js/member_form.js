// Teamlid child sheet: status radio-group, skill combo-box and the period
// block (period_fields.js). The status group posts its own value.
(function () {
  const form = document.querySelector("[data-member-form]");
  if (!form) return;

  const statusGroup = form.querySelector("[data-status-choice]");
  const colleagueField = form.querySelector("[data-colleague-field]");
  const colleagueSelect = form.querySelector("[name$='-colleague']");
  const skillCombo = form.querySelector("[data-skill-choice]");
  const skillInput = form.querySelector("[data-skill-input]");
  const newSkillInput = form.querySelector("[data-new-skill-input]");
  const periodGroup = form.querySelector("[data-period-choice]");
  const inheritInput = form.querySelector("[data-inherit-input]");
  const startInput = form.querySelector("[name$='-placement_start_date']");
  const endInput = form.querySelector("[name$='-placement_end_date']");
  const endKnownSwitch = form.querySelector("[data-end-date-known]");
  const periodHelp = form.querySelector("[data-assignment-period-help]");
  const assignmentStart = form.dataset.assignmentStart || "";
  const assignmentEnd = form.dataset.assignmentEnd || "";

  if (statusGroup) {
    statusGroup.addEventListener("change", (e) => {
      // The group also relays uncheck events from the previous choice.
      if (e.detail && e.detail.checked === false) return;
      const value = e.detail && e.detail.value;
      if (!value) return;
      const filled = value === "ingevuld";
      if (colleagueField) colleagueField.hidden = !filled;
      // An aanvraag names nobody; drop a leftover consultant choice.
      if (!filled && colleagueSelect) colleagueSelect.value = "";
    });
  }

  if (skillCombo && skillInput) {
    // The combo has no name: an existing option posts its id, free text posts
    // skill=__new__ plus the name.
    const optionValues = new Set(
      Array.from(skillCombo.querySelectorAll("nldd-menu-item")).map((item) =>
        item.getAttribute("value"),
      ),
    );
    skillCombo.addEventListener("change", (e) => {
      const value =
        e.detail && e.detail.value !== undefined
          ? e.detail.value
          : skillCombo.value;
      if (!value) {
        skillInput.value = "";
        newSkillInput.value = "";
      } else if (optionValues.has(value)) {
        skillInput.value = value;
        newSkillInput.value = "";
      } else {
        skillInput.value = "__new__";
        newSkillInput.value = value;
      }
    });
  }

  if (!periodGroup) return;

  window.WiesPeriodFields({
    group: periodGroup,
    startInput,
    endInput,
    endKnownSwitch,
    periodHelp,
    inheritStart: assignmentStart,
    inheritEnd: assignmentEnd,
    writeInherit: (inherit) => {
      if (inheritInput) inheritInput.value = inherit ? "on" : "";
    },
  });
})();
