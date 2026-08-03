// PoC: sleep kaarten op het BM-bord — herordenen BINNEN een kolom én verplaatsen
// TUSSEN kolommen, uitsluitend via de drag-handle. Bij een kolomwissel slaan we
// de nieuwe status op.
//
// Eén eigen native-DnD-laag (geen nldd `reorderable`, dat kan alleen binnen één
// lijst). CSP-safe: alle binding hier, geen inline handlers. De move-URL en de
// csrf-token komen uit het template.
(function () {
  const board = document.querySelector(".bm-board");
  if (!board) return;

  const urlTemplate = board.dataset.boardMoveUrlTemplate || "";
  let dragged = null;

  function csrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }

  function moveUrl(assignmentId) {
    return urlTemplate.replace(/0(\/verplaatsen\/?)$/, assignmentId + "$1");
  }

  // Slepen start alléén op de handle, maar we verplaatsen de hele kaart.
  board.addEventListener("dragstart", (e) => {
    const handle = e.target.closest("[data-board-handle]");
    if (!handle) {
      e.preventDefault(); // buiten de handle niet slepen (klik = paneel)
      return;
    }
    dragged = handle.closest("[data-board-card]");
    if (!dragged) return;
    dragged.classList.add("is-dragging");
    e.dataTransfer.effectAllowed = "move";
  });

  board.addEventListener("dragend", () => {
    if (dragged) dragged.classList.remove("is-dragging");
    dragged = null;
    board
      .querySelectorAll(".is-drop-target")
      .forEach((z) => z.classList.remove("is-drop-target"));
  });

  // De kaart waarboven de cursor zweeft; null = onderaan de lijst invoegen.
  function cardAfter(list, y) {
    const cards = [
      ...list.querySelectorAll("[data-board-card]:not(.is-dragging)"),
    ];
    return (
      cards.find(
        (card) =>
          y <
          card.getBoundingClientRect().top +
            card.getBoundingClientRect().height / 2,
      ) || null
    );
  }

  board.addEventListener("dragover", (e) => {
    const list = e.target.closest("[data-board-dropzone]");
    if (!list || !dragged) return;
    e.preventDefault();
    list.classList.add("is-drop-target");
    const ref = cardAfter(list, e.clientY);
    if (ref) list.insertBefore(dragged, ref);
    else list.appendChild(dragged);
  });

  board.addEventListener("dragleave", (e) => {
    const list = e.target.closest("[data-board-dropzone]");
    if (list && !list.contains(e.relatedTarget))
      list.classList.remove("is-drop-target");
  });

  board.addEventListener("drop", (e) => {
    const list = e.target.closest("[data-board-dropzone]");
    if (!list || !dragged) return;
    e.preventDefault();
    list.classList.remove("is-drop-target");

    const column = list.dataset.boardDropzone;
    const originColumn = list.closest(".bm-board__column")?.dataset.boardColumn;
    // dragover heeft de kaart al op z'n plek gezet. Alleen bij een KOLOMWISSEL
    // slaan we de status op; puur herordenen binnen dezelfde kolom hoeft niet.
    if (column === dragged.dataset.originColumn) {
      updateCounts();
      return;
    }
    dragged.dataset.originColumn = column;
    updateCounts();

    const body = new FormData();
    body.append("csrfmiddlewaretoken", csrfToken());
    body.append("kolom", column);
    fetch(moveUrl(dragged.dataset.assignmentId), {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body,
    })
      .then((resp) => {
        if (!resp.ok) window.location.reload(); // 403/422 → herlaad naar de echte staat
      })
      .catch(() => window.location.reload());
  });

  // Onthoud de startkolom per kaart, zodat we bij drop weten of hij wisselde.
  board.querySelectorAll("[data-board-card]").forEach((card) => {
    card.dataset.originColumn = card.closest(
      "[data-board-dropzone]",
    ).dataset.boardDropzone;
  });

  function updateCounts() {
    board.querySelectorAll("[data-board-column]").forEach((col) => {
      const list = col.querySelector("[data-board-dropzone]");
      const badge = col.querySelector("nldd-badge");
      if (list && badge)
        badge.setAttribute(
          "number",
          list.querySelectorAll("[data-board-card]").length,
        );
    });
  }
})();
