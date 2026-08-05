// Prognose chart: available capacity (grey band) vs. planned hours (green area)
// across the horizon. Data arrives via the #prognose-chart[data-forecast]
// attribute (no inline <script>, per the script-src 'self' CSP). Drawn with the
// vendored uPlot library.

(function () {
  "use strict";

  const CAPACITY_COLOR = "#b8b8b8"; // grey — matches "afgerond" in bench.css
  const CAPACITY_FILL = "#e6e6e6";
  const PLANNED_COLOR = "#1f7a4d"; // green — "actief" in bench.css
  const PLANNED_FILL = "rgba(31, 122, 77, 0.55)";
  const AANVRAGEN_COLOR = "#c8781e"; // amber — open requests, stacked on planned
  const AANVRAGEN_FILL = "rgba(200, 120, 30, 0.45)";
  const TODAY_COLOR = "#d52b1e"; // red — "vandaag" marker

  const MONTHS_NL = [
    "jan",
    "feb",
    "mrt",
    "apr",
    "mei",
    "jun",
    "jul",
    "aug",
    "sep",
    "okt",
    "nov",
    "dec",
  ];

  function init() {
    const el = document.getElementById("prognose-chart");
    if (!el || typeof uPlot === "undefined") return;

    let data;
    try {
      data = JSON.parse(el.dataset.forecast);
    } catch (e) {
      return;
    }

    // uPlot wants the x-axis as UNIX seconds and series as parallel arrays.
    const xs = data.weeks.map((iso) => Date.parse(iso) / 1000);
    const capacity = data.capacity;
    const planned = data.planned;
    const aanvragen = data.aanvragen;
    const unfilled = data.unfilled;
    const overcommit = data.overcommit;
    // uPlot has no built-in stacking: plot the cumulative demand (planned +
    // aanvragen) as one filled area and draw the green "planned" fill on top,
    // so the amber band between them reads as the requests stacked on planned.
    const demand = planned.map((p, i) => p + (aanvragen[i] || 0));
    const todaySec = Date.parse(data.today) / 1000;

    // Vertical "vandaag" line, drawn on top of the series each redraw.
    const todayLine = {
      hooks: {
        draw: [
          (u) => {
            const cx = Math.round(u.valToPos(todaySec, "x", true));
            const ctx = u.ctx;
            ctx.save();
            ctx.strokeStyle = TODAY_COLOR;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(cx, u.bbox.top);
            ctx.lineTo(cx, u.bbox.top + u.bbox.height);
            ctx.stroke();
            ctx.restore();
          },
        ],
      },
    };

    const tooltip = makeTooltip(el);

    function fillSeries(stroke, fill) {
      return {
        stroke,
        fill,
        width: 2,
        points: { show: false },
      };
    }

    const opts = {
      width: el.clientWidth || 900,
      height: 420,
      cursor: { y: false, points: { show: true } },
      scales: {
        x: { time: true },
        y: { range: (u, min, max) => [0, max * 1.05] },
      },
      legend: { show: false },
      plugins: [todayLine, tooltip.plugin],
      axes: [
        {
          // Month ticks in Dutch.
          values: (u, splits) =>
            splits.map((s) => {
              const d = new Date(s * 1000);
              const label = MONTHS_NL[d.getMonth()];
              return d.getMonth() === 0 ? label + " " + d.getFullYear() : label;
            }),
          grid: { stroke: "#eee", width: 1 },
          ticks: { stroke: "#ddd", width: 1 },
        },
        {
          label: "uren per week",
          grid: { stroke: "#f0f0f0", width: 1 },
          ticks: { show: false },
        },
      ],
      // Draw order = series order (later paints on top). Capacity (grey) sits
      // behind; the cumulative "demand" amber fill goes next; the green
      // "planned" fill paints last so the amber only shows above the green.
      series: [
        {},
        Object.assign(
          { label: "Beschikbare capaciteit" },
          fillSeries(CAPACITY_COLOR, CAPACITY_FILL),
        ),
        Object.assign(
          { label: "Aanvragen" },
          fillSeries(AANVRAGEN_COLOR, AANVRAGEN_FILL),
        ),
        Object.assign(
          { label: "Ingepland" },
          fillSeries(PLANNED_COLOR, PLANNED_FILL),
        ),
      ],
    };

    const plot = new uPlot(opts, [xs, capacity, demand, planned], el);
    tooltip.attach(plot, {
      weeks: data.weeks,
      capacity,
      planned,
      aanvragen,
      unfilled,
      overcommit,
    });

    // Keep the chart responsive to width changes.
    window.addEventListener("resize", () => {
      plot.setSize({ width: el.clientWidth || 900, height: 420 });
    });
  }

  // A minimal hover tooltip: capaciteit / ingepland / onbezet for the hovered week.
  function makeTooltip(container) {
    const box = document.createElement("div");
    box.className = "prognose-tooltip";
    box.style.display = "none";
    container.appendChild(box);

    let series = null;

    return {
      plugin: {
        hooks: {
          setCursor: [
            (u) => {
              const idx = u.cursor.idx;
              if (idx == null || series == null) {
                box.style.display = "none";
                return;
              }
              const iso = series.weeks[idx];
              const d = new Date(iso);
              const dateLabel =
                d.getDate() +
                " " +
                MONTHS_NL[d.getMonth()] +
                " " +
                d.getFullYear();
              const overcommitLine =
                series.overcommit[idx] > 0
                  ? "<div>Tekort: " + series.overcommit[idx] + " u/wk</div>"
                  : "<div>Onbezet: " +
                    Math.max(series.unfilled[idx], 0) +
                    " u/wk</div>";
              box.innerHTML =
                "<strong>" +
                dateLabel +
                "</strong>" +
                "<div>Capaciteit: " +
                series.capacity[idx] +
                " u/wk</div>" +
                "<div>Ingepland: " +
                series.planned[idx] +
                " u/wk</div>" +
                "<div>Aanvragen: " +
                series.aanvragen[idx] +
                " u/wk</div>" +
                overcommitLine;
              box.style.display = "block";
              const left = u.valToPos(u.data[0][idx], "x");
              box.style.left = left + "px";
              box.style.top = "8px";
            },
          ],
        },
      },
      attach(plot, s) {
        series = s;
      },
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
