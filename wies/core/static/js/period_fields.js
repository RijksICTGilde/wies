// Shared period block: inherit the assignment period or enter the placement's
// own dates. Used by placement_period_toggle.js and member_form.js.
window.WiesPeriodFields = function bindPeriodFields(options) {
  const group = options.group;
  const checkbox = options.checkbox;
  const startInput = options.startInput;
  const endInput = options.endInput;
  const endKnownSwitch = options.endKnownSwitch;
  const periodHelp = options.periodHelp;
  const inheritStart = options.inheritStart || "";
  const inheritEnd = options.inheritEnd || "";
  const writeInherit = options.writeInherit;

  // Hide the whole field, not just the input, or the label stays behind.
  const fieldOf = (el) => el && (el.closest("nldd-form-field") || el);
  const startField = fieldOf(startInput);
  const endField = fieldOf(endInput);
  const endKnownField = fieldOf(endKnownSwitch);

  function inherits() {
    if (!group) return checkbox.checked;
    return group.getAttribute("value") !== "PLACEMENT";
  }

  function endDateKnown() {
    return !endKnownSwitch || endKnownSwitch.hasAttribute("checked");
  }

  // So toggling the switch off and on does not wipe the entered date. An
  // inherited period is not the user's own choice and is not remembered.
  let lastEndDate = endInput ? endInput.value : "";

  function update(inherit, knownOverride) {
    writeInherit(inherit);
    if (periodHelp) periodHelp.hidden = !inherit;
    if (startField) startField.hidden = inherit;
    if (endKnownField) endKnownField.hidden = inherit;
    // knownOverride: during the change event the attribute is not updated yet.
    const known = knownOverride === undefined ? endDateKnown() : knownOverride;
    if (endField) endField.hidden = inherit || !known;
    if (inherit) {
      if (startInput) startInput.value = inheritStart;
      if (endInput) endInput.value = inheritEnd;
    } else if (endInput) {
      if (!known) {
        if (endInput.value) lastEndDate = endInput.value;
        endInput.value = "";
      } else if (!endInput.value) {
        endInput.value = lastEndDate;
      }
    }
  }

  if (group) {
    group.addEventListener("change", (e) => {
      const value = e.detail && e.detail.value;
      update(value ? value === "SERVICE" : inherits());
    });
  } else {
    checkbox.addEventListener("change", (e) =>
      update(e.detail ? e.detail.checked : checkbox.checked),
    );
  }

  if (endKnownSwitch) {
    endKnownSwitch.addEventListener("change", (e) => {
      const known = e.detail ? e.detail.checked : endDateKnown();
      update(inherits(), known);
    });
  }

  update(inherits());
};
