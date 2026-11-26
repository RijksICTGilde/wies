"""Markdown for the free-text descriptions, rendered on the server.

The source stays Markdown in the database (search, CSV and mail read it as
text); this renders it for the panel, the onboarding box and the timeline.
"""

import html
import re
from typing import TYPE_CHECKING

import nh3
from markdown_it import MarkdownIt
from markupsafe import Markup

if TYPE_CHECKING:
    from collections.abc import Iterable

    from markdown_it.token import Token

# js-default: raw HTML is escaped and javascript: links are refused. Off:
# indented code (four leading spaces in an existing description would turn
# into a code block) and setext headings (a line of dashes under a sentence is
# not meant as a heading), and images: the editor cannot insert one and there
# is nothing to host it. breaks: a single newline stays a line break, as it did
# as plain text. linkify: a typed address is a link, as it is in the editor.
_md = (
    MarkdownIt("js-default", {"breaks": True, "linkify": True}).disable(["code", "lheading", "image"]).enable("linkify")
)

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


_WEB = re.compile(r"^(https?:)?//", re.IGNORECASE)


def _complete(href: str) -> str:
    """A link to google.com means the site, not a page under the current URL.
    linkify reads it as it reads an address typed in the text; a path, an
    anchor or tel: is no match and stays as written."""
    match = _md.linkify.match(href)
    if not match or match[0].index != 0 or match[0].last_index != len(href) or match[0].url == href:
        return href
    url = match[0].url
    return "https://" + href if url.startswith("http://") else url


def _link_open(renderer, tokens, idx, options, env):
    token = tokens[idx]
    if token.attrGet("href"):
        token.attrSet("href", _complete(token.attrGet("href")))
    # A link to another site opens beside Wies; mailto:, tel: and #anchor
    # would only leave an empty tab behind.
    new_tab = bool(_WEB.match(token.attrGet("href") or ""))
    if new_tab:
        token.attrSet("target", "_blank")
        token.attrSet("rel", "noopener")
    env.setdefault("new_tab", []).append(new_tab)
    return renderer.renderToken(tokens, idx, options, env)


# As on the site's other links that open a new tab (base.html, contact.html).
_NEW_TAB_NOTE = (
    '<span class="wies-visually-hidden">, opent in nieuw tabblad</span>'
    '<nldd-icon icon="square-arrow-right-top" size="16"></nldd-icon>'
)


def _link_close(renderer, tokens, idx, options, env):
    # Plain text keeps the words only: the note would end up in a sentence.
    announce = env["new_tab"].pop() and not env.get("plain")
    return (_NEW_TAB_NOTE if announce else "") + renderer.renderToken(tokens, idx, options, env)


def _fence(renderer, tokens, idx, options, env):
    # The fence renderer puts a token's attributes on <code>; data-gap has to
    # sit on <pre>, the block the stylesheet spaces.
    gap = tokens[idx].attrs.pop("data-gap", None)
    rendered = renderer.fence(tokens, idx, options, env)
    return rendered.replace("<pre>", f'<pre data-gap="{gap}">', 1) if gap else rendered


# The addresses the editor links by itself (GFM autolinks); linkify would also
# take "google.com" or "//host".
_EDITOR_AUTOLINK = re.compile(r"^(https?://|www\.)", re.IGNORECASE)


def _leads_nowhere(link: Token, text: str) -> bool:
    href = link.attrGet("href") or ""
    if link.markup != "linkify":
        return not href
    return not (_EDITOR_AUTOLINK.match(text) or href.startswith("mailto:"))


def _unlink(state) -> None:
    """Keep the words of a link that leads nowhere, such as [tekst](), and of
    an address the editor does not link either."""
    for block in state.tokens:
        if not block.children:
            continue
        kept, unlinking = [], False
        for i, token in enumerate(block.children):
            if token.type == "link_open":
                # Its text, or its link_close when it has none.
                text = block.children[i + 1].content
                if _leads_nowhere(token, text):
                    unlinking = True
                    continue
                if token.markup == "linkify" and text.lower().startswith("www."):
                    # As the editor does; linkify would make it http://.
                    token.attrSet("href", "https://" + text)
            elif token.type == "link_close" and unlinking:
                unlinking = False
                continue
            kept.append(token)
        block.children = kept


_md.core.ruler.push("unlink", _unlink)
_md.add_render_rule("link_open", _link_open)
_md.add_render_rule("link_close", _link_close)
_md.add_render_rule("heading_open", _heading)
_md.add_render_rule("heading_close", _heading)
_md.add_render_rule("fence", _fence)


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
    html = _md.renderer.render(tokens, _md.options, env)
    # S704 (unsafe Markup) is suppressed: nh3 keeps only the allowlist below.
    return Markup(_sanitize(html))  # noqa: S704


_BLOCK = {"data-gap"}
_ALLOWED = {
    "p": _BLOCK,
    "br": set(),
    "strong": set(),
    "em": set(),
    "s": set(),
    "code": set(),
    "a": {"href", "target", "rel"},
    "span": {"class"},
    "nldd-icon": {"icon", "size"},
    "ul": _BLOCK,
    "ol": _BLOCK | {"start"},
    "li": set(),
    "blockquote": _BLOCK,
    "pre": _BLOCK,
    "hr": _BLOCK,
    **{f"h{n}": _BLOCK | {"data-level"} for n in range(3, 7)},
    **dict.fromkeys(("table", "thead", "tbody", "tr", "th", "td"), _BLOCK),
}


def _sanitize(html: str) -> str:
    """Second line behind the renderer: only the tags, attributes and link
    schemes it is meant to produce. The schemes are those the editor follows."""
    return nh3.clean(
        html,
        tags=set(_ALLOWED),
        attributes=_ALLOWED,
        url_schemes={"http", "https", "mailto", "tel"},
        # The renderer sets rel itself, only on links that open a new tab.
        link_rel=None,
    )


# A block's end separates; an inline tag (<strong>) does not.
_BLOCK_END = re.compile(r"</(?:p|li|h[1-6]|blockquote|pre)>|<br\s*/?>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_STOPS = ".!?:;,"


def join_plain(parts: Iterable[str]) -> str:
    """Plain-text blocks on one line. A block that ends without a stop gets
    "; ", so "- Analyse\n- Advies" does not read as one phrase."""
    text = ""
    for part in filter(None, parts):
        if text:
            text += " " if text[-1] in _STOPS else "; "
        text += part
    return text


def markdown_text(source: str | None) -> str:
    """The plain words of a Markdown source, its blocks on one line."""
    if not source:
        return ""
    blocks = _BLOCK_END.split(_md.render(source, {"plain": True}))
    return join_plain(" ".join(html.unescape(_TAGS.sub("", block)).split()) for block in blocks)


# Past five lines or this many characters a description is cut to five lines
# with "Toon meer". Without JavaScript that is the final word; with it,
# cv_clamp.js hides the button when the clamp cuts nothing.
_LONG_CHARS = 300
_LONG_LINES = 5


def is_long_text(source: str | None) -> bool:
    """Whether a description needs "Toon meer". Empty lines count: the panel
    keeps them as space."""
    if not source:
        return False
    return len(markdown_text(source)) > _LONG_CHARS or len(source.strip().splitlines()) > _LONG_LINES
