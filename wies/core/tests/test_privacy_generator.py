from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from markdown_it import MarkdownIt

from wies.core.management.commands.generate_privacy_html import _render_body, _render_inline


def render(markdown_source: str) -> str:
    md = MarkdownIt("commonmark")
    return _render_body(md.parse(markdown_source))


class RenderBodyTest(SimpleTestCase):
    def test_h2_section_is_wrapped_in_xs_div(self):
        body = render("# Title\n\n## Section\n\nText.\n")
        assert "<c-h1>Title</c-h1>" in body
        assert '<div class="rvo-layout-column rvo-layout-gap--lg">' in body
        assert '<div class="rvo-layout-column rvo-layout-gap--xs">' in body
        assert "<c-h2>Section</c-h2>" in body
        assert "<c-paragraph>Text.</c-paragraph>" in body

    def test_intro_paragraph_is_not_wrapped_in_xs(self):
        body = render("# Title\n\nIntro.\n\n## Section\n\nBody.\n")
        # The intro paragraph appears before any xs wrapper opens.
        intro_idx = body.index("<c-paragraph>Intro.</c-paragraph>")
        xs_idx = body.index('<div class="rvo-layout-column rvo-layout-gap--xs">')
        assert intro_idx < xs_idx

    def test_consecutive_h2s_close_and_reopen_xs_wrapper(self):
        body = render("# T\n\n## A\n\n## B\n\nBody.\n")
        # Two xs wrappers, with a closing </div> between them.
        first = body.index('<div class="rvo-layout-column rvo-layout-gap--xs">')
        between = body.index("</div>", first)
        second = body.index('<div class="rvo-layout-column rvo-layout-gap--xs">', between)
        assert first < between < second

    def test_end_of_document_closes_xs_and_lg_wrappers(self):
        body = render("# T\n\n## A\n\nBody.\n")
        # Should end with two closing divs (xs then lg).
        assert body.rstrip().endswith("</div>\n</div>")

    def test_external_link_gets_target_blank(self):
        body = render("# T\n\n[example](https://example.com)\n")
        assert '<c-link href="https://example.com" target="_blank">example</c-link>' in body

    def test_mailto_link_does_not_get_target_blank(self):
        body = render("# T\n\n[mail](mailto:a@b.nl)\n")
        assert '<c-link href="mailto:a@b.nl">mail</c-link>' in body
        assert "target=" not in body

    def test_list_items_emit_plain_li_without_paragraph_wrapper(self):
        body = render("# T\n\n## L\n\n- one\n- two\n")
        # No <c-paragraph> wrapper inside the list — djlint will tidy the
        # surrounding whitespace later.
        assert "<c-paragraph>" not in body.split("<ul>")[1].split("</ul>")[0]
        assert "<li>" in body
        assert "one" in body

    def test_strong_and_em_pass_through(self):
        body = render("# T\n\n**bold** and *italic*.\n")
        assert "<strong>bold</strong>" in body
        assert "<em>italic</em>" in body


class RenderInlineTest(SimpleTestCase):
    def _inline(self, source: str):
        md = MarkdownIt("commonmark")
        tokens = md.parse(source)
        # First inline token of the first paragraph.
        for tok in tokens:
            if tok.type == "inline":
                return _render_inline(tok.children)
        msg = "no inline token found"
        raise AssertionError(msg)

    def test_text_is_html_escaped(self):
        assert _render_inline(MarkdownIt("commonmark").parseInline("a < b")[0].children) == "a &lt; b"

    def test_relative_link_does_not_get_target_blank(self):
        rendered = self._inline("[home](/home)")
        assert rendered == '<c-link href="/home">home</c-link>'


class StalenessTest(SimpleTestCase):
    """Fails if docs/privacy.md was edited without regenerating privacy.html."""

    def test_privacy_html_is_up_to_date(self):
        try:
            call_command("generate_privacy_html", check=True)
        except CommandError as exc:
            self.fail(str(exc))
