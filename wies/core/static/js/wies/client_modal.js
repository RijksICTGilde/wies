// Opdrachtgever sheet: open it after the htmx swap, and empty the mount point
// once it closes so opening it again works. Cancelling is the title bar dismiss.
(function () {
  "use strict";

  const MODAL_ID = "client-modal";
  const CONTAINER_ID = "client-modal-container";

  function getModal() {
    return document.getElementById(MODAL_ID);
  }

  function openModal(modal) {
    if (!modal) return;
    if (typeof modal.show === "function") {
      modal.show();
    } else {
      customElements.whenDefined("nldd-sheet").then(() => {
        if (typeof modal.show === "function") modal.show();
      });
    }
  }

  function closeModal() {
    const modal = getModal();
    if (!modal) return;
    if (typeof modal.hide === "function") modal.hide();
  }

  document.addEventListener("htmx:afterSettle", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTAINER_ID) return;
    openModal(getModal());
  });

  // Empty the mount point after the sheet closes, so reopening works
  document.addEventListener(
    "close",
    (e) => {
      const path = e.composedPath();
      const modal = path.find(
        (el) => el instanceof Element && el.id === MODAL_ID,
      );
      if (!modal) return;
      const container = document.getElementById(CONTAINER_ID);
      if (container) container.innerHTML = "";
    },
    true,
  );
})();
