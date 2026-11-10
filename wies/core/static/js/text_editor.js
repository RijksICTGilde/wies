// The formatting bar above nldd-text-editor (forms/widgets/text_editor.html).
// The editor is headless: the controls run its commands, and its state event
// sets which controls read as active.
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

  var INLINE = ["bold", "italic", "strikethrough"];
  var HEADING_TEXT = ["Paragraaf", "Kop 1", "Kop 2", "Kop 3"];

  function listOf(active) {
    if (active.orderedList) return "ordered";
    if (active.bulletList) return "bullet";
    return "none";
  }

  // A checkbox group (emphasis): run the command for every key whose desired
  // state differs from the editor's. A radio group (list): the value says
  // which list type is wanted. A toggle (link, quote): one command.
  document.addEventListener("change", function (event) {
    var control = controlIn(event, "[data-editor-group], [data-editor-toggle]");
    if (!control) return;
    var editor = editorOf(control);
    if (!editor || typeof editor.runCommand !== "function") return;
    var active = editor.getState().active;
    var group = control.dataset.editorGroup;
    if (group === "inline") {
      var wanted = new Set(event.detail.values);
      INLINE.forEach(function (key) {
        if (wanted.has(key) !== active[key]) editor.runCommand(key);
      });
    } else if (group === "list") {
      editor.setList(event.detail.value);
    } else {
      editor.runCommand(control.dataset.editorToggle);
    }
    editor.focus();
  });

  // A menu item reports `select`: one in the text-style menu carries the
  // heading level as its value, one in a toolbar item's overflow carries what
  // its twin in the bar does.
  document.addEventListener("select", function (event) {
    var item = controlIn(event, "nldd-menu-item");
    if (!item) return;
    var editor = editorOf(item);
    if (!editor || typeof editor.runCommand !== "function") return;
    var data = item.dataset;
    if (data.editorCommand) editor.runCommand(data.editorCommand);
    else if (data.editorList) editor.setList(data.editorList);
    else if (data.editorHeadingLevel)
      editor.setHeading(Number(data.editorHeadingLevel));
    else if (item.closest("[data-editor-heading]"))
      editor.setHeading(Number(item.getAttribute("value")));
    else return;
    editor.focus();
  });

  function setSelected(wrap, selector, isOn) {
    wrap.querySelectorAll(selector).forEach(function (el) {
      el.toggleAttribute("selected", isOn(el));
    });
  }

  // The other direction: a shortcut (Cmd+B) or a cursor move changes the
  // state, and the controls and their overflow twins follow.
  document.addEventListener("nldd-text-editor-state", function (event) {
    var wrap =
      event.target.closest && event.target.closest("[data-text-editor]");
    if (!wrap) return;
    var active = event.detail.active;
    var list = listOf(active);
    var level = Math.min(active.heading, HEADING_TEXT.length - 1);

    var inline = wrap.querySelector("[data-editor-group='inline']");
    if (inline)
      inline.values = INLINE.filter(function (key) {
        return active[key];
      });
    var listControl = wrap.querySelector("[data-editor-group='list']");
    if (listControl) listControl.value = list;
    setSelected(wrap, "[data-editor-toggle]", function (el) {
      return active[el.dataset.editorToggle];
    });
    setSelected(wrap, "[data-editor-command]", function (el) {
      return active[el.dataset.editorCommand];
    });
    setSelected(wrap, "[data-editor-list]", function (el) {
      return el.dataset.editorList === list;
    });
    setSelected(wrap, "[data-editor-heading-level]", function (el) {
      return Number(el.dataset.editorHeadingLevel) === level;
    });
    var heading = wrap.querySelector("[data-editor-heading]");
    if (heading) {
      heading.setAttribute("text", HEADING_TEXT[level]);
      setSelected(heading, "nldd-menu-item", function (el) {
        return Number(el.getAttribute("value")) === level;
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
