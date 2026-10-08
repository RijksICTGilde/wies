// Teamlid child sheet: status radio-group, skill combo-box and the period
// block (period_fields.js). The status group posts its own value.
(function () {
  const form = document.querySelector("[data-member-form]");
  if (!form) return;

  const statusGroup = form.querySelector("[data-status-choice]");
  const colleagueField = form.querySelector("[data-colleague-field]");
  const colleagueSelect = form.querySelector("[name='colleague']");
  const requestFields = form.querySelectorAll("[data-request-field]");
  const tasksField = form.querySelector("[data-tasks-field]");
  const tasksInput = form.querySelector("[name='description']");
  const requestInput = form.querySelector("[name='request_description']");
  const requestSource = form.querySelector("[data-request-source]");
  const previewToggle = form.querySelector("[data-request-preview-toggle]");
  const preview = form.querySelector("[data-request-preview]");
  const previewText = form.querySelector("[data-request-preview-text]");
  const copyButton = form.querySelector("[data-copy-request]");
  const checkedStatus = form.querySelector("[data-status-choice] [checked]");
  let status = checkedStatus ? checkedStatus.getAttribute("value") : "aanvraag";
  const skillCombo = form.querySelector("[data-skill-choice]");
  const newSkillField = form.querySelector("[data-new-skill-field]");
  const newSkillInput = form.querySelector("[data-new-skill-input]");
  const periodGroup = form.querySelector("[data-period-choice]");
  const inheritInput = form.querySelector("[data-inherit-input]");
  const startInput = form.querySelector("[name='placement_start_date']");
  const endInput = form.querySelector("[name='placement_end_date']");
  const periodHelp = form.querySelector("[data-assignment-period-help]");
  const assignmentStart = form.dataset.assignmentStart || "";
  const assignmentEnd = form.dataset.assignmentEnd || "";

  if (statusGroup) {
    statusGroup.addEventListener("change", (e) => {
      // The group also relays uncheck events from the previous choice.
      if (e.detail && e.detail.checked === false) return;
      const value = e.detail && e.detail.value;
      if (!value) return;
      status = value;
      const filled = value === "ingevuld";
      if (colleagueField) colleagueField.hidden = !filled;
      requestFields.forEach((field) => (field.hidden = filled));
      if (tasksField) tasksField.hidden = !filled;
      // An aanvraag names nobody; drop a leftover consultant choice.
      if (!filled && colleagueSelect) colleagueSelect.value = "";
      renderPeriod();
      updateRequestSource();
    });
  }

  function requestText() {
    return requestInput ? (requestInput.value || "").trim() : "";
  }

  // Only when filling a role that has a vacancy text to offer.
  function updateRequestSource() {
    if (requestSource)
      requestSource.hidden = status !== "ingevuld" || !requestText();
  }

  if (previewToggle && preview) {
    previewToggle.addEventListener("click", () => {
      const open = preview.hidden;
      if (open && previewText) previewText.textContent = requestInput.value;
      preview.hidden = !open;
      previewToggle.toggleAttribute("expanded", open);
      previewToggle.setAttribute(
        "start-icon",
        open ? "chevron-up" : "chevron-down",
      );
      previewToggle.setAttribute(
        "text",
        open
          ? "Omschrijving van de aanvraag verbergen"
          : "Omschrijving van de aanvraag bekijken",
      );
    });
  }

  const copyDialog = document.querySelector("[data-copy-request-dialog]");

  function copyRequest() {
    tasksInput.value = requestInput.value;
    tasksInput.focus();
  }

  if (copyButton && tasksInput) {
    copyButton.addEventListener("click", async () => {
      const current = (tasksInput.value || "").trim();
      // Taken already written by hand are not overwritten unasked.
      if (!current || current === requestText() || !copyDialog) {
        copyRequest();
        return;
      }
      // show() does nothing before Lit has rendered the shadow <dialog>.
      await copyDialog.updateComplete;
      copyDialog.show();
    });
  }

  if (copyDialog) {
    copyDialog
      .querySelector("[data-copy-request-cancel]")
      .addEventListener("click", () => copyDialog.hide());
    copyDialog
      .querySelector("[data-copy-request-confirm]")
      .addEventListener("click", () => {
        copyDialog.hide();
        copyRequest();
      });
  }

  if (skillCombo && newSkillField) {
    // The combo posts `skill` itself. "+ Nieuwe rol" (value __new__) reveals the
    // name field; any other choice hides it and drops a leftover typed name.
    skillCombo.addEventListener("change", (e) => {
      const value =
        e.detail && e.detail.value !== undefined
          ? e.detail.value
          : skillCombo.value;
      const isNew = value === "__new__";
      newSkillField.hidden = !isNew;
      if (!isNew && newSkillInput) newSkillInput.value = "";
    });
  }

  // The period: "Van opdracht" or an own start and end, each a segmented
  // choice with its field under it. The choices post through hidden inputs;
  // the server drops whatever field the choice leaves out.
  const periodBox = form.querySelector("[data-period-box]");
  const startChoiceField = form.querySelector("[data-start-choice-field]");
  const startDate = form.querySelector("[data-start-date]");
  const endDate = form.querySelector("[data-end-date]");
  const duration = form.querySelector("[data-duration]");
  const endChoiceFields = {
    request: form.querySelector("[data-end-choice-field='request']"),
    placement: form.querySelector("[data-end-choice-field='placement']"),
  };
  const startModeInput = form.querySelector("[data-start-mode-input]");
  const endModeInput = form.querySelector("[data-end-mode-input]");

  const choiceValue = (el, fallback) =>
    (el && el.getAttribute("value")) || fallback;
  let inherit = choiceValue(periodGroup, "SERVICE") === "SERVICE";
  let startMode = choiceValue(
    form.querySelector("[data-start-choice]"),
    "DATE",
  );
  const endModes = {
    request: choiceValue(
      endChoiceFields.request &&
        endChoiceFields.request.querySelector("[data-end-choice]"),
      "OPEN",
    ),
    placement: choiceValue(
      endChoiceFields.placement &&
        endChoiceFields.placement.querySelector("[data-end-choice]"),
      "OPEN",
    ),
  };

  function renderPeriod() {
    if (!periodGroup) return;
    const request = status !== "ingevuld";
    const kind = request ? "request" : "placement";
    const startsNow = request && startMode === "NOW";
    const endMode = endModes[kind];
    if (inheritInput) inheritInput.value = inherit ? "on" : "";
    if (periodHelp) periodHelp.hidden = !inherit;
    if (periodBox) periodBox.hidden = inherit;
    if (startChoiceField) startChoiceField.hidden = !request;
    if (startDate) startDate.hidden = startsNow;
    if (endChoiceFields.request) endChoiceFields.request.hidden = !request;
    if (endChoiceFields.placement) endChoiceFields.placement.hidden = request;
    if (endDate) endDate.hidden = endMode !== "DATE";
    if (duration) duration.hidden = endMode !== "DURATION";
    if (startModeInput) startModeInput.value = startsNow ? "NOW" : "DATE";
    if (endModeInput) endModeInput.value = endMode;
  }

  function onChoice(el, apply) {
    if (!el) return;
    el.addEventListener("change", (e) => {
      const value = e.detail && e.detail.value;
      if (value) apply(value);
      renderPeriod();
    });
  }

  onChoice(periodGroup, (value) => {
    inherit = value === "SERVICE";
    // Switching to an own period starts from the opdracht's dates, so a small
    // deviation is one change away.
    if (inherit) return;
    if (startInput && !startInput.value) startInput.value = assignmentStart;
    if (endInput && !endInput.value && assignmentEnd) {
      endInput.value = assignmentEnd;
      Object.keys(endChoiceFields).forEach((kind) => {
        const control =
          endChoiceFields[kind] &&
          endChoiceFields[kind].querySelector("[data-end-choice]");
        if (control) control.value = "DATE";
        endModes[kind] = "DATE";
      });
    }
  });
  onChoice(form.querySelector("[data-start-choice]"), (value) => {
    startMode = value;
  });
  Object.keys(endChoiceFields).forEach((kind) => {
    const field = endChoiceFields[kind];
    onChoice(field && field.querySelector("[data-end-choice]"), (value) => {
      endModes[kind] = value;
    });
  });

  renderPeriod();
})();
