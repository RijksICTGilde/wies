from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from markdown_it import MarkdownIt

from wies.core.management.commands.generate_docs_html import _render_body, _render_inline


def render(markdown_source: str, link_base: str = "") -> str:
    md = MarkdownIt("commonmark")
    return _render_body(md.parse(markdown_source), link_base)


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
        assert '<a href="https://example.com" target="_blank">example' in body

    def test_external_link_announces_the_new_tab(self):
        """The icon is aria-hidden, so the words carry it for a screen reader (#623)."""
        body = render("# T\n\n[example](https://example.com)\n")
        assert "opent in nieuw tabblad" in body
        assert 'icon="square-arrow-right-top"' in body

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


class LinkBaseTest(SimpleTestCase):
    """SECURITY.md links to repo files; on the site those must point at GitHub."""

    BASE = "https://github.com/org/repo/blob/main/"

    def test_relative_link_is_prefixed_and_opens_in_new_tab(self):
        body = render("[cfg](.github/dependabot.yml)\n", link_base=self.BASE)
        assert f'<a href="{self.BASE}.github/dependabot.yml" target="_blank">' in body
        assert "opent in nieuw tabblad" in body

    def test_absolute_anchor_mailto_and_external_links_are_untouched(self):
        for href in ("/home", "#section", "mailto:a@b.nl", "https://example.com"):
            with self.subTest(href=href):
                body = render(f"[x]({href})\n", link_base=self.BASE)
                assert f'href="{href}"' in body

    def test_without_link_base_relative_links_are_untouched(self):
        body = render("[cfg](.github/dependabot.yml)\n")
        assert '<a href=".github/dependabot.yml">cfg</a>' in body


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
    """Fails if docs/privacy.md or SECURITY.md was edited without regenerating its page."""

    def test_doc_pages_are_up_to_date(self):
        try:
            call_command("generate_docs_html", check=True)
        except CommandError as exc:
            self.fail(str(exc))
