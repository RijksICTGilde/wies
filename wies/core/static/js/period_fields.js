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
  // Aanvraag only (member_form.js): "Per direct" in place of a start date and
  // a duration in place of an end date. Absent elsewhere, so the block
  // behaves as before.
  const startsNowSwitch = options.startsNowSwitch;
  const startsNowInput = options.startsNowInput;
  const durationField = options.durationField;
  const isRequest = options.isRequest || (() => false);

  // Hide the whole field, not just the input, or the label stays behind.
  const fieldOf = (el) => el && (el.closest("nldd-form-field") || el);
  const startField = fieldOf(startInput);
  const endField = fieldOf(endInput);
  const endKnownField = fieldOf(endKnownSwitch);
  const startsNowField = fieldOf(startsNowSwitch);

  function inherits() {
    if (!group) return checkbox.checked;
    return group.getAttribute("value") !== "PLACEMENT";
  }

  function endDateKnown() {
    return !endKnownSwitch || endKnownSwitch.hasAttribute("checked");
  }

  function startsNowOn() {
    return !!startsNowSwitch && startsNowSwitch.hasAttribute("checked");
  }

  // So toggling the switch off and on does not wipe the entered date. An
  // inherited period is not the user's own choice and is not remembered.
  let lastEndDate = endInput ? endInput.value : "";

  function update(inherit, knownOverride, startsNowOverride) {
    writeInherit(inherit);
    const request = isRequest();
    // The overrides: during the change event the attribute is not updated yet.
    const startsNow =
      request &&
      (startsNowOverride === undefined ? startsNowOn() : startsNowOverride);
    if (periodHelp) periodHelp.hidden = !inherit;
    if (startsNowField) startsNowField.hidden = inherit || !request;
    if (startsNowInput)
      startsNowInput.value = !inherit && startsNow ? "on" : "";
    if (startField) startField.hidden = inherit || startsNow;
    if (endKnownField) endKnownField.hidden = inherit;
    const known = knownOverride === undefined ? endDateKnown() : knownOverride;
    if (endField) endField.hidden = inherit || !known;
    if (durationField) durationField.hidden = inherit || !request || known;
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

  if (startsNowSwitch) {
    startsNowSwitch.addEventListener("change", (e) => {
      const on = e.detail ? e.detail.checked : startsNowOn();
      update(inherits(), undefined, on);
    });
  }

  update(inherits());
  return { refresh: () => update(inherits()) };
};
