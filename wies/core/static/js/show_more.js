function toggleShowMore(btn) {
  const container = btn.parentElement;
  const truncated = container.querySelector(".truncated-text");
  const full = container.querySelector(".full-text");
  const expanded = full.style.display !== "none";
  truncated.style.display = expanded ? "block" : "none";
  full.style.display = expanded ? "none" : "block";
  btn.querySelector(".show-more-toggle__icon").textContent = expanded
    ? "+"
    : "−";
  btn.querySelector(".show-more-toggle__text").textContent = expanded
    ? "Toon meer"
    : "Toon minder";
}
