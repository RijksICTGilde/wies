"""The description renderer: Markdown in, safe HTML out, plain text unharmed."""

import re
from html.parser import HTMLParser
from unittest import mock

from django.test import SimpleTestCase
from markupsafe import Markup

from wies.core.services.markdown import is_long_text, markdown_text, render_markdown


class RenderMarkdownTest(SimpleTestCase):
    def test_empty_and_whitespace_render_empty(self):
        assert render_markdown("") == ""
        assert render_markdown(None) == ""
        assert render_markdown("   \n ") == ""

    def test_plain_text_keeps_its_line_breaks(self):
        html = render_markdown("Eerste regel\nTweede regel")
        assert "Eerste regel<br>" in html or "Eerste regel<br />" in html
        assert "Tweede regel" in html

    def test_indented_text_is_not_a_code_block(self):
        html = render_markdown("Inleiding\n    ingesprongen vervolg")
        assert "<pre>" not in html
        assert "<code>" not in html
        assert "ingesprongen vervolg" in html

    def test_formatting_renders(self):
        html = render_markdown("**vet** en *cursief*\n- een\n- twee")
        assert "<strong>vet</strong>" in html
        assert "<em>cursief</em>" in html
        assert "<ul>" in html
        assert "<li>een</li>" in html

    def test_headings_render_two_levels_down(self):
        html = render_markdown("# Kop\n## Subkop\n##### Diep")
        assert '<h3 data-level="1">Kop</h3>' in html
        assert '<h4 data-level="2">Subkop</h4>' in html
        assert '<h6 data-level="5">Diep</h6>' in html
        assert "<h1" not in html

    def test_empty_lines_above_a_block_are_kept_as_its_gap(self):
        html = render_markdown("Intro\n**Vet**\n\nTwee\n- een\n- twee\n\n\nDrie\n\n\n\n\nVer")

        assert html.startswith("<p>Intro<br>")
        assert "<ul>" in html
        assert '<p data-gap="2">Drie</p>' in html
        assert '<p data-gap="3">Ver</p>' in html

    def test_a_block_right_under_another_has_no_gap(self):
        html = render_markdown("## Kop\nTekst")

        assert "data-gap" not in html

    def test_a_dashed_line_is_not_a_heading(self):
        html = render_markdown("Zin\n---")
        assert "<h" not in html.replace("<hr>", "").replace("<hr />", "")

    def test_raw_html_and_javascript_links_are_neutralised(self):
        html = render_markdown('<script>alert(1)</script> [x](javascript:alert(1)) <b style="color:red">b</b>')
        assert "<script>" not in html
        # The link is refused and its source stays visible as text, not as href.
        assert 'href="javascript:' not in html
        assert "<a " not in html
        # The raw tag is escaped to text, so no real style attribute survives.
        assert "<b " not in html
        assert "&lt;b style" in html
        assert "&lt;script&gt;" in html

    def test_an_image_is_not_rendered(self):
        html = render_markdown("Kijk ![logo](https://example.org/x.png)")
        assert "<img" not in html
        assert 'Kijk !<a href="https://example.org/x.png"' in html

    def test_typed_addresses_link_as_in_the_editor(self):
        html = render_markdown("www.wies.nl, https://x.nl/pad en anke@rijksoverheid.nl")
        assert '<a href="https://www.wies.nl" target="_blank" rel="noopener">www.wies.nl<span' in html
        assert '<a href="https://x.nl/pad" target="_blank" rel="noopener">https://x.nl/pad<span' in html
        assert '<a href="mailto:anke@rijksoverheid.nl">anke@rijksoverheid.nl</a>' in html

    def test_a_bare_domain_stays_text(self):
        # The editor does not link it either.
        html = render_markdown("google.com en //x.nl")
        assert "<a" not in html

    def test_a_link_reading_www_keeps_its_target(self):
        html = render_markdown("[www.a.nl](https://b.nl/)")
        assert 'href="https://b.nl/"' in html

    def test_a_scheme_the_editor_does_not_follow_loses_its_href(self):
        html = render_markdown("[f](ftp://x.nl/bestand)")
        assert "ftp:" not in html
        assert "f" in html

    def test_links_open_beside_wies(self):
        html = render_markdown("[Wies](https://example.org/)")
        assert (
            '<a href="https://example.org/" target="_blank" rel="noopener">Wies<span class="wies-visually-hidden">, opent in nieuw tabblad</span>'
            in html
        )
        assert 'icon="square-arrow-right-top"' in html

    def test_only_a_link_that_opens_a_tab_says_so(self):
        html = render_markdown("[m](mailto:a@b.nl) en [w](https://example.org/)")
        assert html.count("opent in nieuw tabblad") == 1

    def test_plain_text_leaves_the_new_tab_note_out(self):
        assert markdown_text("Zie [Wies](https://example.org/) hier") == "Zie Wies hier"

    def test_mail_phone_anchor_and_own_links_stay_in_place(self):
        # A new tab there would stay empty, or show Wies a second time.
        html = render_markdown("[m](mailto:a@b.nl) [t](tel:0612345678) [a](#kop) [o](/opdrachten/)")
        assert "target=" not in html

    def test_a_link_without_scheme_gets_https(self):
        # Otherwise the browser resolves "google.com" under the current page.
        html = render_markdown("[zoek](google.com) en [hier](/opdrachten/) en [mail](mailto:a@b.nl)")
        assert 'href="https://google.com"' in html
        assert 'href="/opdrachten/"' in html
        assert 'href="mailto:a@b.nl"' in html

    def test_an_address_without_scheme_becomes_a_mail_link(self):
        html = render_markdown("[mail](anke@rijksoverheid.nl) en [pad](example.org/@team)")
        assert '<a href="mailto:anke@rijksoverheid.nl">mail</a>' in html
        assert 'href="https://example.org/@team"' in html

    def test_a_host_with_a_port_gets_https(self):
        # Read as a scheme, "wies.nl:" would leave a link that opens nothing.
        html = render_markdown("[pad](wies.nl:8080/pad) [bel](tel:0612345678)")
        assert 'href="https://wies.nl:8080/pad"' in html
        assert 'href="tel:0612345678"' in html

    def test_a_lone_asterisk_stays(self):
        html = render_markdown("2 * 3 = 6")
        assert "2 * 3 = 6" in html

    def test_a_link_without_target_stays_text(self):
        html = render_markdown("[leeg]() en **[vet]()**")
        assert "<a" not in html
        assert "leeg en <strong>vet</strong>" in html

    def test_a_gap_above_a_code_fence_lands_on_pre(self):
        # The stylesheet spaces the children of nldd-rich-text; <code> is not one.
        html = render_markdown("Tekst\n\n```\ncode\n```")
        assert '<pre data-gap="1"><code>' in html

    def test_output_is_markup(self):
        assert isinstance(render_markdown("x"), Markup)


class MarkdownTextTest(SimpleTestCase):
    def test_plain_text_drops_the_formatting(self):
        assert (
            markdown_text("# Kop\n\n**vet** en [link](https://x.nl)\n\n- een\n- twee") == "Kop; vet en link; een; twee"
        )

    def test_a_block_with_its_own_stop_needs_no_separator(self):
        assert markdown_text("Eerste zin.\n\nTaken:\n- analyse") == "Eerste zin. Taken: analyse"

    def test_empty_gives_empty(self):
        assert markdown_text(None) == ""
        assert markdown_text("") == ""


class IsLongTextTest(SimpleTestCase):
    def test_short_text_is_not_long(self):
        assert not is_long_text(None)
        assert not is_long_text("Een\n\nvijf\nregels\nlang")

    def test_six_lines_including_empty_ones_are_long(self):
        # The panel keeps an empty line as space, so it takes a line too.
        assert is_long_text("Een\n\ntwee\n\ndrie\nvier")

    def test_characters_count_without_the_marks(self):
        assert not is_long_text("**" + "x" * 300 + "**")
        assert is_long_text("x" * 301)


# From the OWASP XSS Filter Evasion Cheat Sheet, written as Markdown can
# carry them: raw HTML, link and image targets, autolinks, references, link
# titles and fence info strings.
XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<<script>script>alert(1)<</script>/script>",
    "<img src=x onerror=alert(1)>",
    "<IMG SRC=JaVaScRiPt:alert(1)>",
    "<svg onload=alert(1)>",
    "<svg><script>alert(1)</script></svg>",
    "<iframe src=javascript:alert(1)></iframe>",
    '<a href="javascript:alert(1)">x</a>',
    "<style>*{background:url(javascript:alert(1))}</style>",
    "<body onload=alert(1)>",
    "[x](javascript:alert(1))",
    "[x](JaVaScRiPt:alert(1))",
    "[x](javascript&#58;alert(1))",
    "[x](&#106;avascript:alert(1))",
    "[x](&#x6A;avascript:alert(1))",
    "[x](<java script:alert(1)>)",
    "[x](java\u0000script:alert(1))",
    "[x]( javascript:alert(1))",
    "[x](\x01javascript:alert(1))",
    "[x](javascript\x0b:alert(1))",
    "[x](jav&#x09;ascript:alert(1))",
    "[x](jav&#x0A;ascript:alert(1))",
    "[x](jav&#x0D;ascript:alert(1))",
    "[x](&#0000106&#0000097vascript:alert(1))",
    "[x](&#x6A&#x61vascript:alert(1))",
    "[x](&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;alert(1))",
    "[x](%6A%61vascript:alert(1))",
    "[x](vbscript:msgbox(1))",
    "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
    "[x](file:///etc/passwd)",
    "[x](smb://host/share)",
    "![x](javascript:alert(1))",
    "![x](x onerror=alert(1))",
    "<javascript:alert(1)>",
    "[x][r]\n\n[r]: javascript:alert(1)",
    '[x](https://a.nl "t\\" onmouseover=\\"alert(1)")',
    '[x](https://a.nl" onclick="alert(1))',
    'www.a.nl"onmouseover="alert(1)',
    'a@b.nl"onclick="alert(1)',
    '```" onclick="alert(1)\nx\n```',
    "```js onclick=alert(1)\nx\n```",
    "**<img src=x onerror=alert(1)>**",
    "- [x](javascript:alert(1))\n> <script>alert(1)</script>",
]
SAFE_SCHEMES = {"http", "https", "mailto", "tel"}
# Browsers drop these from a URL before they read its scheme.
_URL_NOISE = re.compile(r"[\x00-\x20\x7f-\x9f]")
_SCHEME = re.compile(r"^([a-z][a-z0-9+.-]*):", re.IGNORECASE)


class _Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _tags(html: str) -> list[tuple[str, dict]]:
    parser = _Tags()
    parser.feed(html)
    return parser.tags


class XssTest(SimpleTestCase):
    def test_no_payload_gets_a_script_a_handler_or_an_unsafe_link(self):
        for payload in XSS_PAYLOADS:
            with self.subTest(payload=payload):
                for tag, attrs in _tags(render_markdown(payload)):
                    assert tag not in {"script", "img", "svg", "iframe", "style", "body"}
                    assert not [name for name in attrs if name.startswith("on") or name == "style"]
                    scheme = _SCHEME.match(_URL_NOISE.sub("", attrs.get("href") or ""))
                    assert scheme is None or scheme[1].lower() in SAFE_SCHEMES

    def test_the_sanitizer_leaves_the_renderers_own_output_alone(self):
        source = (
            "# Kop\n\nTekst met **vet**, *cursief*, ~~weg~~ en `code`.\n\n\n"
            "- een\n- [link](https://example.org/)\n\n3. drie\n\n> citaat\n\n"
            "---\n\n```\ncode\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
            "[mail](a@b.nl) [bel](tel:0612345678) [anker](#kop) [pad](/opdrachten/)"
        )
        unsanitized = mock.patch("wies.core.services.markdown._sanitize", side_effect=lambda html: html)
        with unsanitized:
            expected = render_markdown(source)

        assert render_markdown(source) == expected
        assert 'data-level="1"' in expected
        assert 'data-gap="2"' in expected
        assert '<nldd-icon icon="square-arrow-right-top"' in expected
