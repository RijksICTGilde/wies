"""Guard the `script-src 'self'` CSP at the source: the templates.

The CSP has no 'unsafe-inline' and no nonce, so any inline JavaScript that
creeps back in is blocked by the browser *silently* — a dead button with only a
console warning, which no functional test and no reviewer reliably catches.
These tests fail the build instead.

The `@click`/`@keydown`/... check is the sharp one: jinja-roos-components
compiles those component attributes to `onclick=`/`onkeydown=` in
_generic_attributes.j2, so `<c-button @click="...">` looks perfectly idiomatic
and still produces inline JavaScript. Bind via data-action + ui_handlers.js
instead.
"""

import re
from pathlib import Path

from django.test import TestCase

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "jinja2"

# `on<event>="` — the quote requirement keeps prose ("... on maandag=") out.
INLINE_HANDLER = re.compile(r"""\son[a-z]+\s*=\s*["']""")

# jinja-roos-components event attributes, which render as on*= handlers.
COMPONENT_HANDLER = re.compile(r"""\s@[a-z]+\s*=\s*["']""")

# A <script> tag without a src attribute, i.e. an inline block.
INLINE_SCRIPT = re.compile(r"""<script(?![^>]*\ssrc\s*=)[^>]*>""")

# htmx's inline-scripting attribute and javascript: URLs.
HX_ON = re.compile(r"""\shx-on[a-z:-]*\s*=""")
JAVASCRIPT_URL = re.compile(r"""=\s*["']\s*javascript:""", re.IGNORECASE)

CHECKS = (
    (INLINE_HANDLER, 'inline event handler (on*="...")'),
    (COMPONENT_HANDLER, 'component event attribute (@click="...", renders as onclick=)'),
    (INLINE_SCRIPT, "inline <script> block (no src)"),
    (HX_ON, "hx-on attribute (inline script)"),
    (JAVASCRIPT_URL, "javascript: URL"),
)


def _templates() -> list[Path]:
    return sorted(TEMPLATE_DIR.rglob("*.html"))


class NoInlineJavaScriptInTemplatesTest(TestCase):
    """No template may contain JavaScript that `script-src 'self'` would block."""

    def test_templates_are_found(self):
        # A wrong TEMPLATE_DIR would make every check below pass vacuously.
        assert len(_templates()) > 20

    def test_no_inline_javascript(self):
        violations = []
        for template in _templates():
            source = template.read_text(encoding="utf-8")
            for line_number, line in enumerate(source.splitlines(), start=1):
                for pattern, description in CHECKS:
                    if pattern.search(line):
                        relative = template.relative_to(TEMPLATE_DIR)
                        violations.append(f"{relative}:{line_number}: {description}\n    {line.strip()}")

        assert not violations, (
            "Inline JavaScript found in templates. The Content-Security-Policy "
            "(script-src 'self') blocks it silently in the browser.\n"
            "Move the code to a file in wies/core/static/js/ and bind it with a "
            "data-action attribute — see wies/core/static/js/ui_handlers.js.\n\n" + "\n".join(violations)
        )


class DataActionBindingsTest(TestCase):
    """Every data-action in a template must resolve to a handler, and vice
    versa. A typo in either place is otherwise a silently dead button."""

    UI_HANDLERS = TEMPLATE_DIR.parent / "static" / "js" / "ui_handlers.js"

    def _registered_actions(self) -> set[str]:
        source = self.UI_HANDLERS.read_text(encoding="utf-8")
        registry = re.search(r"var CLICK_ACTIONS = \{(.*?)\n  \};", source, re.DOTALL)
        assert registry, "Could not locate CLICK_ACTIONS in ui_handlers.js"
        return set(re.findall(r"""["']([a-z-]+)["']\s*:""", registry.group(1)))

    def _used_actions(self) -> dict[str, str]:
        used = {}
        for template in _templates():
            for action in re.findall(r"""data-action=["']([^"']+)["']""", template.read_text(encoding="utf-8")):
                used.setdefault(action, str(template.relative_to(TEMPLATE_DIR)))
        return used

    def test_every_used_action_has_a_handler(self):
        unknown = {
            action: path for action, path in self._used_actions().items() if action not in self._registered_actions()
        }
        assert not unknown, f"data-action without a CLICK_ACTIONS entry in ui_handlers.js: {unknown}"

    def test_every_handler_is_used(self):
        unused = self._registered_actions() - set(self._used_actions())
        assert not unused, f"CLICK_ACTIONS entries no longer used by any template: {sorted(unused)}"
