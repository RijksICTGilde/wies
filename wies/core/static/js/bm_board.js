// Dragging assignment cards between the status columns of the BM board.
//
// Native drag-and-drop rather than nldd-list's own reordering: that works
// within a single list, and the whole point here is moving a card from one
// column to another. Only the grip starts a drag, so a plain click on the card
// still opens the side panel.
(function () {
  "use strict";

  const GRID_ID = "bm-board-grid";
  const CARD = "[data-board-card]";
  const DROPZONE = "[data-board-dropzone]";
  const DROP_TARGET_CLASS = "is-drop-target";
  const DRAGGING_CLASS = "is-dragging";

  // The card being dragged. dataTransfer would be the natural place for this,
  // but its data is unreadable during dragover in most browsers, which is
  // exactly when we need to know whether we may drop.
  let dragged = null;

  function grid() {
    return document.getElementById(GRID_ID);
  }

  function cardFor(target) {
    return target instanceof Element ? target.closest(CARD) : null;
  }

  function moveUrl(publicId) {
    const template = grid()?.dataset.boardMoveUrlTemplate;
    if (!template) return null;
    // The template is the reverse() of the move route with a placeholder uuid;
    // swapping it keeps the URL shape in urls.py rather than hardcoded here.
    return template.replace(/[0-9a-f-]{36}/i, publicId);
  }

  function csrfToken() {
    return grid()?.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
  }

  function clearDropTargets() {
    grid()
      ?.querySelectorAll("." + DROP_TARGET_CLASS)
      .forEach((el) => el.classList.remove(DROP_TARGET_CLASS));
  }

  function setupDragStart() {
    document.addEventListener("dragstart", (e) => {
      // Only from the grip: dragging the card body would fight the link.
      const handle =
        e.target instanceof Element && e.target.closest("[data-board-handle]");
      const card = handle && cardFor(handle);
      if (!card) return;
      dragged = card;
      card.classList.add(DRAGGING_CLASS);
      e.dataTransfer.effectAllowed = "move";
      // Firefox starts no drag at all unless something is set here.
      e.dataTransfer.setData("text/plain", card.dataset.assignmentId || "");
    });

    document.addEventListener("dragend", () => {
      dragged?.classList.remove(DRAGGING_CLASS);
      dragged = null;
      clearDropTargets();
    });
  }

  function setupDropZones() {
    document.addEventListener("dragover", (e) => {
      if (!dragged) return;
      const zone = e.target instanceof Element && e.target.closest(DROPZONE);
      if (!zone) return;
      // Without preventDefault the browser refuses the drop entirely.
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      if (!zone.classList.contains(DROP_TARGET_CLASS)) {
        clearDropTargets();
        zone.classList.add(DROP_TARGET_CLASS);
      }
    });

    document.addEventListener("drop", (e) => {
      if (!dragged) return;
      const zone = e.target instanceof Element && e.target.closest(DROPZONE);
      if (!zone) return;
      e.preventDefault();
      const status = zone.dataset.boardDropzone;
      const card = dragged;
      clearDropTargets();
      // Dropping a card back where it came from is not a move.
      if (!status || zone.contains(card)) return;
      moveCard(card, status);
    });
  }

  function moveCard(card, status) {
    const url = moveUrl(card.dataset.assignmentId);
    const token = csrfToken();
    if (!url || !token || !window.htmx) return;

    // Show the move immediately; the server response re-renders the columns and
    // corrects the counts (and puts the card back if the move was refused).
    window.htmx.ajax("POST", url, {
      target: "#" + GRID_ID,
      swap: "outerHTML",
      values: { status: status, csrfmiddlewaretoken: token },
    });
  }

  function init() {
    setupDragStart();
    setupDropZones();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
