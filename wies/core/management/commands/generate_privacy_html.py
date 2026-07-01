import subprocess
import tempfile
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from markdown_it import MarkdownIt

MD_PATH = Path(settings.BASE_DIR) / "docs" / "privacy.md"
HTML_PATH = Path(settings.BASE_DIR) / "wies" / "core" / "jinja2" / "privacy.html"

PREAMBLE = """\
{# AUTO-GENERATED FROM docs/privacy.md by `manage.py generate_privacy_html`. DO NOT EDIT BY HAND. #}
{% extends "base.html" %}
{% block title %}
  Privacy - Wies
{% endblock title %}
{% block sidebar %}
  {% include "parts/general_sidebar.html" %}
{% endblock sidebar %}
{% block content %}
  <nldd-container padding="24">
  <nldd-rich-text>
"""

POSTAMBLE = "  </nldd-rich-text>\n  </nldd-container>\n{% endblock content %}\n"


def _render_inline(children) -> str:  # noqa: C901 — dispatch table over markdown-it token types; splitting hides the mapping
    out: list[str] = []
    for tok in children:
        if tok.type == "text":
            out.append(escape(tok.content, quote=False))
        elif tok.type == "strong_open":
            out.append("<strong>")
        elif tok.type == "strong_close":
            out.append("</strong>")
        elif tok.type == "em_open":
            out.append("<em>")
        elif tok.type == "em_close":
            out.append("</em>")
        elif tok.type == "softbreak":
            out.append("\n")
        elif tok.type == "hardbreak":
            out.append("<br>\n")
        elif tok.type == "link_open":
            href = tok.attrGet("href") or ""
            attrs = f' href="{escape(href, quote=True)}"'
            if href.startswith(("http://", "https://")):
                attrs += ' target="_blank"'
            out.append(f"<a{attrs}>")
        elif tok.type == "link_close":
            out.append("</a>")
        elif tok.type == "code_inline":
            out.append(f"<code>{escape(tok.content, quote=False)}</code>")
    return "".join(out)


def _render_body(tokens) -> str:
    # nldd-rich-text styles semantic HTML directly, so we emit plain
    # <h1>/<h2>/<p>/<ul> without RVO layout wrappers.
    out: list[str] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open" and tok.tag in ("h1", "h2"):
            inline = tokens[i + 1]
            out.append(f"<{tok.tag}>{_render_inline(inline.children)}</{tok.tag}>")
            i += 3
            continue
        if tok.type == "paragraph_open":
            inline = tokens[i + 1]
            rendered_inline = _render_inline(inline.children)
            if tok.hidden:
                out.append(rendered_inline)
            else:
                out.append(f"<p>{rendered_inline}</p>")
            i += 3
            continue
        if tok.type == "bullet_list_open":
            out.append("<ul>")
            i += 1
            continue
        if tok.type == "bullet_list_close":
            out.append("</ul>")
            i += 1
            continue
        if tok.type == "list_item_open":
            out.append("<li>")
            i += 1
            continue
        if tok.type == "list_item_close":
            out.append("</li>")
            i += 1
            continue
        i += 1

    return "\n".join(out)


def render_privacy_template(markdown_source: str) -> str:
    """Render the privacy markdown source to the final Jinja2 template string.

    The output is djlint-formatted to keep pre-commit comparisons stable.
    """
    md = MarkdownIt("commonmark")
    tokens = md.parse(markdown_source)
    body = _render_body(tokens)
    raw = PREAMBLE + body + "\n" + POSTAMBLE
    return _djlint_format(raw)


def _djlint_format(content: str) -> str:
    """Format ``content`` with djlint to match the project's house style.

    djlint exits non-zero when it makes changes (even with ``--reformat``), so
    we deliberately do not pass ``check=True``. The file is rewritten in place;
    we read it back and return the formatted text.
    """
    djlint_bin = Path(settings.BASE_DIR) / ".venv" / "bin" / "djlint"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(  # noqa: S603 — fixed argv, paths under BASE_DIR
            [str(djlint_bin), str(tmp_path), "--reformat", "--profile=jinja", "--indent=2", "--quiet"],
            check=False,
            capture_output=True,
        )
        return tmp_path.read_text(encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)


class Command(BaseCommand):
    help = "Regenerate wies/core/jinja2/privacy.html from docs/privacy.md."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit non-zero if the rendered output differs from the file on disk. Does not write.",
        )

    def handle(self, *args, **options):
        rendered = render_privacy_template(MD_PATH.read_text(encoding="utf-8"))
        if options["check"]:
            current = HTML_PATH.read_text(encoding="utf-8")
            if current != rendered:
                msg = (
                    "privacy.html is out of date. "
                    "Run `uv run python manage.py generate_privacy_html` and commit the result."
                )
                raise CommandError(msg)
            self.stdout.write(self.style.SUCCESS("privacy.html is up to date."))
            return
        HTML_PATH.write_text(rendered, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {HTML_PATH.relative_to(settings.BASE_DIR)}"))
