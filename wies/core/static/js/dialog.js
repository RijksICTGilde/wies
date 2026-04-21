// HTMX + Dialog integration - hybrid approach
document.addEventListener("htmx:afterSwap", function (e) {
  // When HTMX loads modal content into a container, find any dialogs and show them
  const dialogs = e.detail.target.querySelectorAll('dialog[closedby="any"]');

  dialogs.forEach(function (dialog) {
    // Auto-show dialog when HTMX loads content
    if (dialog.innerHTML.trim()) {
      dialog.showModal();
      document.documentElement.style.overflow = "hidden";
    }

    // Unlock scroll when dialog closes
    dialog.addEventListener("close", function () {
      document.documentElement.style.overflow = "";
    });

    // Add close button listeners for .close elements (PR #116 style)
    const closeElements = dialog.querySelectorAll(".close");
    closeElements.forEach(function (element) {
      element.addEventListener("click", function () {
        dialog.close();
      });
    });
  });

  // NDD: auto-show ndd-window when HTMX loads content
  const windows = e.detail.target.querySelectorAll("ndd-window");
  windows.forEach(function (win) {
    if (typeof win.show === "function") {
      win.show();
    } else {
      customElements.whenDefined("ndd-window").then(() => win.show());
    }
  });
});

// Listen for closeModal trigger from server
document.addEventListener("closeModal", function () {
  // Close any open modal dialogs
  const modalContainers = [
    "labelFormModal",
    "userFormModal",
    "clientModalContainer",
  ];
  modalContainers.forEach((modalId) => {
    const modalContainer = document.getElementById(modalId);
    if (modalContainer) {
      const dialog = modalContainer.querySelector("dialog");
      if (dialog) dialog.close();
      const win = modalContainer.querySelector("ndd-window");
      if (win && typeof win.hide === "function") win.hide();
    }
  });
});
