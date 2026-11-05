import posixpath
import re
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from markdown_it import MarkdownIt

from wies.core.handboek import HANDBOEK_PAGES


@dataclass(frozen=True)
class DocPage:
    """A markdown document rendered to an in-product page behind the footer."""

    source: str  # relative to BASE_DIR
    target: str  # relative to BASE_DIR
    title: str
    # Prefix for repo-relative links (``.github/...``), which would 404 on the site.
    link_base: str = ""
    # Handbook pages share a menu and give their sections an anchor.
    handboek: bool = False


PAGES = [
    DocPage("docs/privacy.md", "wies/core/jinja2/privacy.html", "Privacy"),
    DocPage(
        "SECURITY.md",
        "wies/core/jinja2/security.html",
        "Beveiliging",
        link_base="https://github.com/RijksICTGilde/wies/blob/main/",
    ),
    *(
        DocPage(
            page.source,
            f"wies/core/jinja2/{page.template}",
            f"{page.title} · Handboek",
            link_base="https://github.com/RijksICTGilde/wies/blob/main/docs/handboek/",
            handboek=True,
        )
        for page in HANDBOEK_PAGES
    ),
]

PREAMBLE = """\
{{# AUTO-GENERATED FROM {source} by `manage.py generate_docs_html`. DO NOT EDIT BY HAND. #}}
{{% extends "base_footer.html" %}}
{{% block title %}}
  {title} · Wies
{{% endblock title %}}
"""

CONTENT_OPEN = "{% block footer_content %}\n  <nldd-rich-text>\n"

HANDBOEK_SIDEBAR = """\
{{% block sidebar %}}
  {{% with handboek_sections = {sections} %}}
    {{% include "parts/handboek_sidebar.html" %}}
  {{% endwith %}}
{{% endblock sidebar %}}
"""

HANDBOEK_INLINE_MENU = """\
{{% with handboek_sections = {sections} %}}
  {{% include "parts/handboek_menu_inline.html" %}}
{{% endwith %}}"""

POSTAMBLE = "  </nldd-rich-text>\n{% endblock footer_content %}\n"

EXTERNAL_LINK_AFFORDANCE = (
    '<span class="wies-visually-hidden">, opent in nieuw tabblad</span>'
    '<nldd-icon icon="square-arrow-right-top" size="16"></nldd-icon>'
)


def _escape(text: str) -> str:
    """HTML-escape ``text``, double quotes and braces included: the output is a
    Jinja2 template, so a quoted ``{{ ... }}`` would otherwise run as code, and a
    quoted ``data-action="x"`` would read as a binding to the template checks."""
    escaped = escape(text, quote=False).replace('"', "&quot;")
    if "{" in escaped or "}" in escaped:
        return "{% raw %}" + escaped + "{% endraw %}"
    return escaped


def _app_urls() -> dict[str, str]:
    """Repo files that Wies shows as a page of its own, by repo path, as the Jinja
    expression for their URL."""
    return {
        "docs/privacy.md": "{{ url('privacy') }}",
        "SECURITY.md": "{{ url('beveiliging') }}",
        **{
            page.source: "{{ url('handboek') }}"
            if page is HANDBOEK_PAGES[0]
            else f"{{{{ url('handboek-page', args=['{page.slug}']) }}}}"
            for page in HANDBOEK_PAGES
        },
    }


TEMPLATE_DIR = "wies/core/jinja2/"

# Fewer sections fit on a screen and need no submenu.
SUBMENU_MIN_SECTIONS = 4


def _image(src: str, source: str) -> str:
    """An image is an SVG in the template dir, inlined so it can use the colour
    tokens and follow the light/dark scheme; GitHub shows the same file as an image."""
    path = posixpath.normpath(posixpath.join(posixpath.dirname(source), src))
    if not path.startswith(TEMPLATE_DIR) or not path.endswith(".svg"):
        msg = f"{source}: images must be SVGs under {TEMPLATE_DIR}, got {src}"
        raise CommandError(msg)
    return f'{{% include "{path.removeprefix(TEMPLATE_DIR)}" %}}'


def _app_href(href: str, source: str) -> str | None:
    """The in-app URL for a relative link to a document Wies shows itself."""
    if not source or href.startswith(("/", "#", "mailto:")) or "://" in href:
        return None
    path, _, fragment = href.partition("#")
    app_url = _app_urls().get(posixpath.normpath(posixpath.join(posixpath.dirname(source), path)))
    if app_url is None:
        return None
    return f"{app_url}#{escape(fragment, quote=True)}" if fragment else app_url


def _resolve_href(href: str, link_base: str) -> str:
    if not link_base or href.startswith(("/", "#", "mailto:")) or "://" in href:
        return href
    return link_base + href


def _render_inline(children, link_base: str = "", source: str = "") -> str:  # noqa: C901 — dispatch table over markdown-it token types; splitting hides the mapping
    out: list[str] = []
    external_depth = 0
    for tok in children:
        if tok.type == "text":
            out.append(_escape(tok.content))
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
            raw_href = tok.attrGet("href") or ""
            app_href = _app_href(raw_href, source)
            if app_href:
                out.append(f'<a href="{app_href}">')
                continue
            href = _resolve_href(raw_href, link_base)
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
            out.append(f"<code>{_escape(tok.content)}</code>")
        elif tok.type == "image":
            out.append(_image(tok.attrGet("src") or "", source))
    return "".join(out)


_PLAIN_TAGS = {
    "bullet_list_open": "<ul>",
    "bullet_list_close": "</ul>",
    "ordered_list_close": "</ol>",
    "list_item_open": "<li>",
    "list_item_close": "</li>",
    "thead_open": "<thead>",
    "thead_close": "</thead>",
    "tbody_open": "<tbody>",
    "tbody_close": "</tbody>",
    "tr_open": "<tr>",
    "tr_close": "</tr>",
    "th_open": '<th scope="col">',
    "th_close": "</th>",
    "td_open": "<td>",
    "td_close": "</td>",
    "table_close": "</table></div>",
}


def _plain_text(inline) -> str:
    return "".join(child.content for child in inline.children if child.type in ("text", "code_inline"))


def _table_open(caption: str) -> str:
    # Same shape as the role matrix: a wide table scrolls in its own focusable box
    # (WCAG 1.4.10), named after the section it sits in.
    label = _escape(caption)
    return (
        f'<div class="wies-table-scroll" tabindex="0" role="region" aria-label="{label}">'
        f'<table><caption class="wies-visually-hidden">{label}</caption>'
    )


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _sections(tokens) -> list[tuple[str, str]]:
    """``[(anchor, title)]`` for every h2, with anchors made unique."""
    sections: list[tuple[str, str]] = []
    seen: set[str] = set()
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open" or tok.tag != "h2":
            continue
        title = _plain_text(tokens[i + 1])
        anchor = base = _slug(title)
        n = 2
        while anchor in seen:
            anchor, n = f"{base}-{n}", n + 1
        seen.add(anchor)
        sections.append((anchor, title))
    return sections


def _render_body(tokens, link_base: str = "", anchors: list[str] | None = None, source: str = "") -> str:
    # nldd-rich-text styles semantic HTML directly, so no RVO layout wrappers.
    out: list[str] = []
    section = ""
    next_anchor = iter(anchors or [])

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open" and tok.tag in ("h1", "h2", "h3"):
            inline = tokens[i + 1]
            section = _plain_text(inline)
            anchor = next(next_anchor, None) if tok.tag == "h2" else None
            id_attr = f' id="{anchor}"' if anchor else ""
            out.append(f"<{tok.tag}{id_attr}>{_render_inline(inline.children, link_base, source)}</{tok.tag}>")
            i += 3
            continue
        if tok.type in _PLAIN_TAGS:
            out.append(_PLAIN_TAGS[tok.type])
            i += 1
            continue
        if tok.type == "ordered_list_open":
            start = tok.attrGet("start")
            out.append(f'<ol start="{start}">' if start else "<ol>")
            i += 1
            continue
        if tok.type == "table_open":
            out.append(_table_open(section))
            i += 1
            continue
        if tok.type == "inline":
            out.append(_render_inline(tok.children, link_base, source))
            i += 1
            continue
        if tok.type in ("fence", "code_block"):
            out.append(f"<pre><code>{_escape(tok.content.rstrip())}</code></pre>")
            i += 1
            continue
        if tok.type == "paragraph_open":
            inline = tokens[i + 1]
            rendered_inline = _render_inline(inline.children, link_base, source)
            if tok.hidden:
                out.append(rendered_inline)
            else:
                out.append(f"<p>{rendered_inline}</p>")
            i += 3
            continue
        i += 1

    return "\n".join(out)


def _markdown() -> MarkdownIt:
    return MarkdownIt("commonmark").enable("table")


def render_doc_template(markdown_source: str, page: DocPage) -> str:
    """Render a page's markdown source to the final Jinja2 template string.

    The output is djlint-formatted to keep pre-commit comparisons stable.
    """
    tokens = _markdown().parse(markdown_source)
    sections = _sections(tokens) if page.handboek else []
    body = _render_body(tokens, page.link_base, [anchor for anchor, _title in sections], page.source)
    menu = ""
    if page.handboek:
        # A long page lists its sections under it in the menu; the template gets them as a literal.
        listed = sections if len(sections) >= SUBMENU_MIN_SECTIONS else []
        literal = repr([list(section) for section in listed])
        menu = HANDBOEK_SIDEBAR.format(sections=literal)
        body = body.replace("</h1>", "</h1>\n" + HANDBOEK_INLINE_MENU.format(sections=literal), 1)
    raw = PREAMBLE.format(source=page.source, title=page.title) + menu + CONTENT_OPEN + body + "\n" + POSTAMBLE
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
    help = "Regenerate the in-product pages rendered from markdown (privacy, security, the handbook)."

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
