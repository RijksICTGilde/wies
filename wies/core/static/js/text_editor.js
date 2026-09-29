// The formatting bar above nldd-text-editor (forms/widgets/text_editor.html).
// The editor is headless: the controls run its commands, and its state event
// sets which controls read as active. Same shape as the design system's story.
(function () {
  "use strict";

  function editorOf(el) {
    var wrap = el.closest("[data-text-editor]");
    return wrap ? wrap.querySelector("nldd-text-editor") : null;
  }

  function controlIn(event, selector) {
    return event.composedPath().find(function (el) {
      return el instanceof Element && el.matches(selector);
    });
  }

  // The editor wraps exactly the selection, spaces included, and Markdown
  // does not read "** woord**" as emphasis: the marker may not touch a space
  // on the inside. So the selection loses its outer whitespace first. Only
  // for the buttons; a shortcut (Cmd+B) runs inside the component.
  function trimSelection(editor) {
    var view = editor.view;
    if (!view) return;
    var sel = view.state.selection.main;
    if (sel.empty) return;
    var text = view.state.sliceDoc(sel.from, sel.to);
    var lead = text.length - text.trimStart().length;
    var trail = text.length - text.trimEnd().length;
    if (!lead && !trail) return;
    var from = sel.from + lead;
    var to = sel.to - trail;
    if (from < to) view.dispatch({ selection: { anchor: from, head: to } });
  }

  var INLINE = ["bold", "italic", "strikethrough"];
  var HEADING_TEXT = ["Paragraaf", "Kop 1", "Kop 2", "Kop 3"];

  // A checkbox group (emphasis): run the command for every key whose desired
  // state differs from the editor's. A radio group (list): the value says
  // which list type is wanted. A toggle (link, quote): one command.
  document.addEventListener("change", function (event) {
    var control = controlIn(event, "[data-editor-group], [data-editor-toggle]");
    if (!control) return;
    var editor = editorOf(control);
    if (!editor || typeof editor.runCommand !== "function") return;
    var active = editor.getState().active || {};
    var group = control.dataset.editorGroup;
    if (group === "inline") {
      var wanted = new Set(
        (event.detail && event.detail.values) || control.values || [],
      );
      trimSelection(editor);
      INLINE.forEach(function (key) {
        if (wanted.has(key) !== Boolean(active[key])) editor.runCommand(key);
      });
    } else if (group === "list") {
      editor.setList(
        (event.detail && event.detail.value) || control.value || "none",
      );
    } else {
      editor.runCommand(control.dataset.editorToggle);
    }
    editor.focus();
  });

  // The text-style menu: a menu item reports `select`; its value is the
  // heading level, 0 for a paragraph.
  document.addEventListener("select", function (event) {
    var item = controlIn(event, "nldd-menu-item");
    var button = item && item.closest("[data-editor-heading]");
    if (!button) return;
    var editor = editorOf(button);
    if (!editor || typeof editor.setHeading !== "function") return;
    editor.setHeading(Number(item.getAttribute("value")) || 0);
    editor.focus();
  });

  // The other direction: a shortcut (Cmd+B) or a cursor move changes the
  // state, and the controls follow.
  document.addEventListener("nldd-text-editor-state", function (event) {
    var wrap =
      event.target.closest && event.target.closest("[data-text-editor]");
    if (!wrap) return;
    var active = (event.detail && event.detail.active) || {};
    var inline = wrap.querySelector("[data-editor-group='inline']");
    if (inline)
      inline.values = INLINE.filter(function (key) {
        return active[key];
      });
    var list = wrap.querySelector("[data-editor-group='list']");
    if (list)
      list.value = active.orderedList
        ? "ordered"
        : active.bulletList
          ? "bullet"
          : "none";
    wrap.querySelectorAll("[data-editor-toggle]").forEach(function (toggle) {
      toggle.toggleAttribute(
        "selected",
        Boolean(active[toggle.dataset.editorToggle]),
      );
    });
    var heading = wrap.querySelector("[data-editor-heading]");
    if (heading) {
      var level = Math.min(
        Number(active.heading) || 0,
        HEADING_TEXT.length - 1,
      );
      heading.setAttribute("text", HEADING_TEXT[level]);
      heading.querySelectorAll("nldd-menu-item").forEach(function (item) {
        item.toggleAttribute(
          "selected",
          Number(item.getAttribute("value")) === level,
        );
      });
    }
  });

  // autofocus on the editor does nothing before its CodeMirror view exists
  // (focus() is a no-op until then), so wait for the render after a swap.
  function focusAutofocused(root) {
    var editor =
      root.querySelector && root.querySelector("nldd-text-editor[autofocus]");
    if (!editor) return;
    customElements
      .whenDefined("nldd-text-editor")
      .then(function () {
        return editor.updateComplete;
      })
      .then(function () {
        editor.focus();
      });
  }

  document.addEventListener("htmx:afterSettle", function (event) {
    if (event.detail && event.detail.target)
      focusAutofocused(event.detail.target);
  });
})();
