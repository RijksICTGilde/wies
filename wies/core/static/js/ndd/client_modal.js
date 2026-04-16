// NDD client modal — open ndd-modal-dialog na HTMX swap, sluit via data-ndd-action.
(function () {
  "use strict";

  const MODAL_ID = "ndd-client-modal";
  const CONTAINER_ID = "ndd-client-modal-container";

  function getModal() {
    return document.getElementById(MODAL_ID);
  }

  function openModal(modal) {
    if (!modal) return;
    if (modal.shadowRoot) {
      if (typeof modal.show === "function") modal.show();
      else if (typeof modal.open === "function") modal.open();
    } else {
      customElements.whenDefined("ndd-modal-dialog").then(() => {
        if (typeof modal.show === "function") modal.show();
        else if (typeof modal.open === "function") modal.open();
      });
    }
  }

  function closeModal() {
    const modal = getModal();
    if (!modal) return;
    if (typeof modal.hide === "function") modal.hide();
    else if (typeof modal.close === "function") modal.close();
  }

  document.addEventListener("htmx:afterSettle", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTAINER_ID) return;
    openModal(getModal());
  });

  document.addEventListener("click", (e) => {
    const path = e.composedPath();
    const btn = path.find(
      (el) =>
        el instanceof Element &&
        el.dataset &&
        el.dataset.nddAction === "client-modal-close",
    );
    if (!btn) return;
    e.preventDefault();
    closeModal();
  });

  // Cleanup container nadat modal sluit zodat herhalend openen werkt
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
