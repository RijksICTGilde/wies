// Side panel navigation and history management.
// Dialog open/close is handled by dialog.js (via closedby="any").
// This file handles: URL sync, panel navigation stack, popstate.

const panelStack = [];
let _skipNextPush = false;

// --- Panel actions ---

function swapPanel(url) {
  const panel = document.getElementById("side_panel");
  if (panel && panel.open) {
    htmx.ajax("GET", url, {
      target: "#side_panel-content",
      headers: { "HX-Target": "side_panel-content" },
    });
  } else {
    htmx.ajax("GET", url, {
      target: "#side_panel-container",
      headers: { "HX-Target": "side_panel-container" },
    });
  }
}

function closeSidePanel() {
  panelStack.length = 0;
  const panel = document.getElementById("side_panel");
  if (panel) panel.close();
  document.getElementById("side_panel-container").innerHTML = "";
  document.documentElement.style.overflow = "";

  const url = new URL(window.location);
  url.searchParams.delete("collega");
  url.searchParams.delete("opdracht");
  history.replaceState({}, "", url.toString());
}

function panelBack() {
  if (panelStack.length > 0) {
    const prevUrl = panelStack.pop();
    const url = new URL(prevUrl, window.location.origin);

    if (url.searchParams.has("collega") || url.searchParams.has("opdracht")) {
      history.replaceState({}, "", prevUrl);
      _skipNextPush = true;
      swapPanel(prevUrl);
    } else {
      closeSidePanel();
    }
  } else {
    closeSidePanel();
  }
}

// --- Event listeners ---

document.addEventListener("DOMContentLoaded", function () {
  // Open server-rendered panel on page load
  const panel = document.getElementById("side_panel");
  if (panel && panel.innerHTML.trim()) {
    panel.showModal();
    document.documentElement.style.overflow = "hidden";
  }

  // ESC key → close (capturing so it works on replaced dialogs)
  const container = document.getElementById("side_panel-container");
  if (container) {
    container.addEventListener(
      "cancel",
      function (e) {
        e.preventDefault();
        closeSidePanel();
      },
      true,
    );
  }
});

// After HTMX panel swaps: push URL and track in panel stack.
// Skipped when triggered by popstate or panelBack (they manage history themselves).
document.addEventListener("htmx:afterSettle", function (event) {
  const targetId = event.detail.target?.id;
  if (targetId !== "side_panel-container" && targetId !== "side_panel-content")
    return;

  if (_skipNextPush) {
    _skipNextPush = false;
    return;
  }

  const requestPath =
    event.detail.pathInfo?.requestPath || event.detail.requestConfig?.path;
  if (!requestPath) return;

  const reqUrl = new URL(requestPath, window.location.origin);
  const reqPath = reqUrl.pathname + reqUrl.search;
  const currentPath = window.location.pathname + window.location.search;

  if (reqPath !== currentPath) {
    panelStack.push(currentPath);
    history.pushState({}, "", reqPath);
  }
});

// Backdrop click → close (unless an inline-edit form is open)
document.addEventListener("click", function (e) {
  const panel = document.getElementById("side_panel");
  if (panel && panel.open && e.target === panel) {
    if (panel.querySelector("form[hx-post]")) return;
    closeSidePanel();
  }
});

// Browser back/forward
window.addEventListener("popstate", function () {
  const url = new URL(window.location);
  const hasPanel =
    url.searchParams.has("collega") || url.searchParams.has("opdracht");
  const panel = document.getElementById("side_panel");

  if (!hasPanel && panel && panel.open) {
    panelStack.length = 0;
    panel.close();
    document.getElementById("side_panel-container").innerHTML = "";
    document.documentElement.style.overflow = "";
  } else if (hasPanel) {
    _skipNextPush = true;
    swapPanel(window.location.href);
  }
});

// --- Tab switching (event delegation for HTMX-swapped content) ---

document.addEventListener("click", (e) => {
  const tab = e.target.closest(".rvo-tabs__tab");
  if (!tab) return;
  const tabsContainer = tab.closest(".rvo-tabs");
  const allTabs = [...tabsContainer.querySelectorAll(".rvo-tabs__tab")];
  const index = allTabs.indexOf(tab);
  allTabs.forEach((t, i) => {
    t.classList.toggle("rvo-tabs__tab--active", i === index);
    t.setAttribute("aria-selected", i === index);
    t.setAttribute("tabindex", i === index ? "0" : "-1");
  });
  const panels = tabsContainer.querySelectorAll(".rvo-tabs__panel");
  panels.forEach((p, i) => {
    if (i === index) {
      p.removeAttribute("hidden");
      p.setAttribute("tabindex", "0");
    } else {
      p.setAttribute("hidden", "");
      p.setAttribute("tabindex", "-1");
    }
  });
});
