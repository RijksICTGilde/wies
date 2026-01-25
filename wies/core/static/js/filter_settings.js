document.addEventListener("htmx:afterSwap", function (event) {
  if (event.detail.target.id === "filter-list") {
    const movedItem = event.detail.target.querySelector(
      ".filter-order-item--moved",
    );
    if (movedItem) {
      const direction = movedItem.dataset.movedDirection;
      const buttonText = direction === "up" ? "Omhoog" : "Omlaag";
      const fallbackText = direction === "up" ? "Omlaag" : "Omhoog";

      const buttons = movedItem.querySelectorAll("button");
      const button =
        Array.from(buttons).find((btn) =>
          btn.textContent.includes(buttonText),
        ) ||
        Array.from(buttons).find((btn) =>
          btn.textContent.includes(fallbackText),
        );

      if (button) {
        button.focus();
      }
    }
  }
});
