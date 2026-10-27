import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from markdown_it import MarkdownIt


@dataclass(frozen=True)
class DocPage:
    """A markdown document rendered to an in-product page behind the footer."""

    source: str  # relative to BASE_DIR
    target: str  # relative to BASE_DIR
    title: str
    # Prefix for repo-relative links (``.github/...``), which would 404 on the site.
    link_base: str = ""


PAGES = [
    DocPage("docs/privacy.md", "wies/core/jinja2/privacy.html", "Privacy"),
    DocPage(
        "SECURITY.md",
        "wies/core/jinja2/security.html",
        "Beveiliging",
        link_base="https://github.com/RijksICTGilde/wies/blob/main/",
    ),
]

PREAMBLE = """\
{{# AUTO-GENERATED FROM {source} by `manage.py generate_docs_html`. DO NOT EDIT BY HAND. #}}
{{% extends "base_footer.html" %}}
{{% block title %}}
  {title} · Wies
{{% endblock title %}}
{{% block footer_content %}}
  <nldd-rich-text>
"""

POSTAMBLE = "  </nldd-rich-text>\n{% endblock footer_content %}\n"

EXTERNAL_LINK_AFFORDANCE = (
    '<span class="wies-visually-hidden">, opent in nieuw tabblad</span>'
    '<nldd-icon icon="square-arrow-right-top" size="16"></nldd-icon>'
)


def _resolve_href(href: str, link_base: str) -> str:
    if not link_base or href.startswith(("/", "#", "mailto:")) or "://" in href:
        return href
    return link_base + href


def _render_inline(children, link_base: str = "") -> str:  # noqa: C901 — dispatch table over markdown-it token types; splitting hides the mapping
    out: list[str] = []
    external_depth = 0
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
            href = _resolve_href(tok.attrGet("href") or "", link_base)
            attrs = f' href="{escape(href, quote=True)}"'
            if href.startswith(("http://", "https://")):
                attrs += ' target="_blank"'
                external_depth += 1
            out.append(f"<a{attrs}>")
        elif tok.type == "link_close":
            # A new tab has to be announced before it opens (#623); the icon is
            # aria-hidden, so the words go in visually-hidden text beside it.
            if external_depth:
                external_depth -= 1
                out.append(EXTERNAL_LINK_AFFORDANCE)
            out.append("</a>")
        elif tok.type == "code_inline":
            out.append(f"<code>{escape(tok.content, quote=False)}</code>")
    return "".join(out)


def _render_body(tokens, link_base: str = "") -> str:
    # nldd-rich-text styles semantic HTML directly, so no RVO layout wrappers.
    out: list[str] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open" and tok.tag in ("h1", "h2"):
            inline = tokens[i + 1]
            out.append(f"<{tok.tag}>{_render_inline(inline.children, link_base)}</{tok.tag}>")
            i += 3
            continue
        if tok.type == "paragraph_open":
            inline = tokens[i + 1]
            rendered_inline = _render_inline(inline.children, link_base)
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


def render_doc_template(markdown_source: str, page: DocPage) -> str:
    """Render a page's markdown source to the final Jinja2 template string.

    The output is djlint-formatted to keep pre-commit comparisons stable.
    """
    md = MarkdownIt("commonmark")
    tokens = md.parse(markdown_source)
    body = _render_body(tokens, page.link_base)
    raw = PREAMBLE.format(source=page.source, title=page.title) + body + "\n" + POSTAMBLE
    return _djlint_format(raw)


def _djlint_format(content: str) -> str:
    """Format ``content`` with djlint to match the project's house style.

    The ``--profile``/``--indent`` flags are passed explicitly and MUST stay in
    sync with what the ``djlint-reformat-jinja`` pre-commit hook produces (see
    ``.pre-commit-config.yaml``). djlint does not reliably read ``[tool.djlint]``
    from ``pyproject.toml`` here, so relying on that config instead of these flags
    yields a different indentation than the hook -- the hook then reformats the
    generated file on commit and ``test_doc_pages_are_up_to_date`` fails.

    djlint exits non-zero when it makes changes (even with ``--reformat``), so
    we deliberately do not pass ``check=True``. The file is rewritten in place;
    we read it back and return the formatted text.
    """
    # Resolve djlint from PATH: it lives in the active venv (/opt/venv in the
    # container image, .venv locally). It is NOT at BASE_DIR/.venv -- inside the
    # container that path is the bind-mounted host (macOS) venv, whose binaries
    # can't execute on Linux.
    djlint_bin = shutil.which("djlint")
    if djlint_bin is None:
        msg = "djlint not found on PATH; install the dev dependency group (uv sync --group dev)."
        raise CommandError(msg)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(  # noqa: S603 — argv from shutil.which + paths under BASE_DIR
            [djlint_bin, str(tmp_path), "--reformat", "--profile=jinja", "--indent=2", "--quiet"],
            check=False,
            capture_output=True,
        )
        return tmp_path.read_text(encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)


class Command(BaseCommand):
    help = "Regenerate the in-product pages rendered from markdown (privacy, security)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit non-zero if the rendered output differs from the files on disk. Does not write.",
        )

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        stale: list[str] = []
        for page in PAGES:
            rendered = render_doc_template((base_dir / page.source).read_text(encoding="utf-8"), page)
            target = base_dir / page.target
            if options["check"]:
                if not target.exists() or target.read_text(encoding="utf-8") != rendered:
                    stale.append(page.target)
                continue
            target.write_text(rendered, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote {page.target}"))
        if stale:
            msg = (
                f"Out of date: {', '.join(stale)}. "
                "Run `uv run python manage.py generate_docs_html` and commit the result."
            )
            raise CommandError(msg)
        if options["check"]:
            self.stdout.write(self.style.SUCCESS("All generated pages are up to date."))
