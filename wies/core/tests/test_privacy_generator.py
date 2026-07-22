from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from markdown_it import MarkdownIt

from wies.core.management.commands.generate_privacy_html import _render_body, _render_inline


def render(markdown_source: str) -> str:
    md = MarkdownIt("commonmark")
    return _render_body(md.parse(markdown_source))


class RenderBodyTest(SimpleTestCase):
    def test_headings_and_paragraph_use_plain_html(self):
        body = render("# Title\n\n## Section\n\nText.\n")
        # nldd-rich-text styles semantic HTML directly — no RVO layout wrappers.
        assert "<h1>Title</h1>" in body
        assert "<h2>Section</h2>" in body
        assert "<p>Text.</p>" in body
        assert "rvo-layout-column" not in body
        assert "<c-" not in body

    def test_external_link_gets_target_blank(self):
        body = render("# T\n\n[example](https://example.com)\n")
        assert '<a href="https://example.com" target="_blank">example</a>' in body

    def test_mailto_link_does_not_get_target_blank(self):
        body = render("# T\n\n[mail](mailto:a@b.nl)\n")
        assert '<a href="mailto:a@b.nl">mail</a>' in body
        assert "target=" not in body

    def test_list_items_emit_plain_li_without_paragraph_wrapper(self):
        body = render("# T\n\n## L\n\n- one\n- two\n")
        # No <p> wrapper inside the list — djlint will tidy the
        # surrounding whitespace later.
        assert "<p>" not in body.split("<ul>")[1].split("</ul>")[0]
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
        assert rendered == '<a href="/home">home</a>'


class StalenessTest(SimpleTestCase):
    """Fails if docs/privacy.md was edited without regenerating privacy.html."""

    def test_privacy_html_is_up_to_date(self):
        try:
            call_command("generate_privacy_html", check=True)
        except CommandError as exc:
            self.fail(str(exc))
