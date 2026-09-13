// Prognose chart: per-month bars whose LENGTH is proportional to the demand
// (ingepland + aanvragen) as a percentage of the available capacity. A dashed
// line marks 100% (capacity); a bar that runs above it is over capacity. Data
// arrives via the #prognose-chart[data-forecast] attribute (no inline <script>,
// per the script-src 'self' CSP). Plain DOM — POC, no chart library needed.

(function () {
  "use strict";

  // Top of the y-axis, in percent. Bars are scaled against this, so equal
  // lengths always mean equal percentages. Give some headroom above 100% so
  // over-capacity months have room to stand taller.
  const AXIS_MAX = 120;

  function init() {
    const el = document.getElementById("prognose-chart");
    const select = document.getElementById("prognose-year");
    if (!el || !select) return;

    let data;
    try {
      data = JSON.parse(el.dataset.forecast);
    } catch (e) {
      return;
    }

    // Populate the year dropdown, defaulting to the current year.
    data.years.forEach((year) => {
      const opt = document.createElement("option");
      opt.value = year;
      opt.textContent = year;
      if (year === data.current_year) opt.selected = true;
      select.appendChild(opt);
    });

    function render(year) {
      const months = data.by_year[year] || [];
      el.innerHTML = "";

      const chart = document.createElement("div");
      chart.className = "prognose-bars";

      // Dashed 100%-capacity reference line, positioned on the same absolute
      // scale as the bars (100 of AXIS_MAX from the bottom).
      const capLine = document.createElement("div");
      capLine.className = "prognose-capline";
      capLine.style.bottom = (100 / AXIS_MAX) * 100 + "%";
      const capLabel = document.createElement("span");
      capLabel.className = "prognose-capline__label";
      capLabel.textContent = "100%";
      capLine.appendChild(capLabel);
      chart.appendChild(capLine);

      months.forEach((m) => {
        const col = document.createElement("div");
        col.className =
          "prognose-bar-col" + (m.is_current ? " is-current" : "");

        // The bar stacks from the bottom up; its total length is proportional to
        // ingepland + aanvragen on the absolute (0..AXIS_MAX) scale.
        const bar = document.createElement("div");
        bar.className = "prognose-bar";

        bar.title =
          m.label +
          " " +
          year +
          "\nIngepland: " +
          m.planned_pct +
          "%\nAanvragen: " +
          m.aanvragen_pct +
          "%" +
          (m.overcommit_pct > 0
            ? "\nBoven capaciteit: +" + m.overcommit_pct + "%"
            : "\nVrij: " + m.free_pct + "%");

        bar.appendChild(segment("planned", m.planned_pct));
        bar.appendChild(segment("aanvragen", m.aanvragen_pct));

        const label = document.createElement("div");
        label.className = "prognose-bar-label";
        label.textContent = m.label;

        // A column is a full-height track (the axis) with the bar pinned to the
        // bottom and the month label beneath it.
        const track = document.createElement("div");
        track.className = "prognose-bar-track";
        track.appendChild(bar);

        col.appendChild(track);
        col.appendChild(label);
        chart.appendChild(col);
      });

      el.appendChild(chart);
    }

    // A segment's height is its share of the FULL axis, so 20% and 40% segments
    // differ in length by exactly 2×.
    function segment(kind, pct) {
      const seg = document.createElement("div");
      seg.className = "prognose-bar-seg prognose-bar-seg--" + kind;
      seg.style.height = (pct / AXIS_MAX) * 100 + "%";
      if (pct >= 6) {
        const v = document.createElement("span");
        v.className = "prognose-bar-value";
        v.textContent = Math.round(pct) + "%";
        seg.appendChild(v);
      }
      return seg;
    }

    select.addEventListener("change", () => render(select.value));
    render(select.value || data.current_year);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
