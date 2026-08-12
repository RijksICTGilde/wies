// Drives the teamlid child sheet (assignment_member_edit_panel_content.html).
//
// Mirrors placement_period_toggle.js for the period block, plus the member
// specifics: the status radio-group and the skill combo-box. The status group
// posts its own value (nldd-radio-button-field is form-associated since design
// system 0.8.71), so this only reacts to the choice. The period choice still
// posts through [data-inherit-input] ("on" = neem opdrachtperiode over, "" =
// eigen periode).
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
    // The combo itself has no name; translate its choice into the form
    // contract: an existing option posts its id, free text posts as a new
    // role (skill=__new__ plus the name).
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
