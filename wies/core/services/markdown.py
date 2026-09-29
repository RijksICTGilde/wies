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
# out two levels down (h3), never above the page's structure.
_HEADING_SHIFT = 2


def _heading(renderer, tokens, idx, options, env):
    level = min(int(tokens[idx].tag[1]) + _HEADING_SHIFT, 6)
    tokens[idx].tag = f"h{level}"
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


def render_markdown(source: str | None) -> Markup:
    """Markdown source to safe HTML; empty in, empty out."""
    if not source or not source.strip():
        return Markup("")
    # S704 (unsafe Markup) is suppressed: the renderer escapes raw HTML and
    # refuses javascript: links (js-default preset), so the output is safe.
    return Markup(_md.render(source))  # noqa: S704


# A block's end is a word boundary; an inline tag (<strong>) is not.
_BLOCK_END = re.compile(r"</(?:p|li|h[1-6]|blockquote|ul|ol)>|<br\s*/?>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def markdown_text(source: str | None) -> str:
    """The plain words of a Markdown source, one space between them."""
    if not source:
        return ""
    stripped = _TAGS.sub("", _BLOCK_END.sub(" ", _md.render(source)))
    return " ".join(html.unescape(stripped).split())


def markdown_excerpt(source: str | None, limit: int = 200) -> str:
    """The first sentence, as plain text, for a one-line summary of a description."""
    text = markdown_text(source)
    first = _SENTENCE_END.split(text, maxsplit=1)[0]
    if len(first) > limit:
        first = first[: limit - 1].rstrip() + "…"
    return first
