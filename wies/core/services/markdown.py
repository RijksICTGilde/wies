"""Markdown for the free-text descriptions, rendered on the server.

The source stays Markdown in the database (search, CSV and mail read it as
text); this renders it for the panel, the onboarding box and the timeline.
"""

import html
import re

from markdown_it import MarkdownIt
from markupsafe import Markup

# js-default: raw HTML is escaped and javascript: links are refused. Off:
# images (nothing to host them), indented code (four leading spaces in an
# existing description would turn into a code block) and setext headings (a
# line of dashes under a sentence is not meant as a heading). breaks: a
# single newline stays a line break, as it did as plain text.
_md = MarkdownIt("js-default", {"breaks": True}).disable(["image", "code", "lheading"])

# A description sits under the panel's own h2 headings, so its "# Kop" comes
# out two levels down (h3), never above the page's structure. data-level keeps
# the level that was written, so it can look as it does in the editor.
_HEADING_SHIFT = 2


def _heading(renderer, tokens, idx, options, env):
    written = int(tokens[idx].tag[1])
    tokens[idx].tag = f"h{min(written + _HEADING_SHIFT, 6)}"
    if tokens[idx].nesting == 1:
        tokens[idx].attrSet("data-level", str(written))
    return renderer.renderToken(tokens, idx, options, env)


# Anything with a scheme, or a path on this site.
_ABSOLUTE = re.compile(r"^([a-z][a-z0-9+.-]*:|/|#)", re.IGNORECASE)


def _link_open(renderer, tokens, idx, options, env):
    token = tokens[idx]
    href = token.attrGet("href") or ""
    # "google.com" in a description means the site, not a page under the
    # current URL; without a scheme the browser would resolve it relative.
    if href and not _ABSOLUTE.match(href):
        token.attrSet("href", "https://" + href)
    # A description's link leaves the panel; open it beside Wies.
    token.attrSet("target", "_blank")
    token.attrSet("rel", "noopener")
    return renderer.renderToken(tokens, idx, options, env)


_md.add_render_rule("link_open", _link_open)
_md.add_render_rule("heading_open", _heading)
_md.add_render_rule("heading_close", _heading)


# More empty lines than this read as a mistake, not as a wider gap.
_MAX_GAP = 3


def _mark_gaps(tokens, lines: list[str]) -> None:
    """Give each top-level block the number of empty lines above it.

    Markdown folds any run of empty lines into one block break, and the editor
    shows them as typed; data-gap lets the stylesheet put the space back. A
    list's range runs on over the empty lines after it, hence the trim.
    """
    previous_end = None
    for token in tokens:
        if token.level != 0 or token.nesting == -1 or token.map is None:
            continue
        start, end = token.map
        if previous_end is not None and start > previous_end:
            token.attrSet("data-gap", str(min(start - previous_end, _MAX_GAP)))
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        previous_end = end


def render_markdown(source: str | None) -> Markup:
    """Markdown source to safe HTML; empty in, empty out."""
    if not source or not source.strip():
        return Markup("")
    env: dict = {}
    tokens = _md.parse(source, env)
    _mark_gaps(tokens, source.splitlines())
    # S704 (unsafe Markup) is suppressed: the renderer escapes raw HTML and
    # refuses javascript: links (js-default preset), so the output is safe.
    return Markup(_md.renderer.render(tokens, _md.options, env))  # noqa: S704


# A block's end is a word boundary; an inline tag (<strong>) is not.
_BLOCK_END = re.compile(r"</(?:p|li|h[1-6]|blockquote|ul|ol)>|<br\s*/?>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")


def markdown_text(source: str | None) -> str:
    """The plain words of a Markdown source, one space between them."""
    if not source:
        return ""
    stripped = _TAGS.sub("", _BLOCK_END.sub(" ", _md.render(source)))
    return " ".join(html.unescape(stripped).split())
