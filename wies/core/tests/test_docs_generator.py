import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from jinja2 import Template
from markdown_it import MarkdownIt

from wies.core.management.commands.generate_docs_html import (
    DocPage,
    _markdown,
    _render_body,
    _render_inline,
    _sections,
    render_doc_template,
)


def render(markdown_source: str, link_base: str = "") -> str:
    return _render_body(_markdown().parse(markdown_source), link_base)


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

    def test_third_level_heading(self):
        assert "<h3>Sub</h3>" in render("### Sub\n")

    def test_ordered_list_keeps_its_start_number(self):
        assert "<ol>" in render("1. a\n2. b\n")
        assert '<ol start="7">' in render("7. a\n8. b\n")

    def test_table_has_column_headers_and_is_named_after_its_section(self):
        body = render("## Rollen\n\n| Rol | Mag |\n| --- | --- |\n| BM | Ja |\n").replace("\n", "")
        assert 'role="region" aria-label="Rollen"' in body
        assert '<caption class="wies-visually-hidden">Rollen</caption>' in body
        assert '<th scope="col">Rol</th>' in body
        assert "<td>Ja</td>" in body

    def test_code_block_is_escaped(self):
        body = render("```python\nif a < b:\n```\n")
        assert "<pre><code>if a &lt; b:</code></pre>" in body

    def test_jinja_delimiters_in_text_do_not_run(self):
        """The output is a Jinja2 template: a quoted ``{{ ... }}`` must stay text."""
        body = render("Use `{{ inline_edit(obj) }}` or {% if %}.\n")
        assert "<code>{% raw %}{{ inline_edit(obj) }}{% endraw %}</code>" in body
        assert Template(body).render() == "<p>Use <code>{{ inline_edit(obj) }}</code> or {% if %}.</p>"


class HandboekPageTest(SimpleTestCase):
    SOURCE = (
        "# Titel\n\nIntro.\n\n## Data, privacy & meer\n\n## Één keer\n\n## Één keer\n\n"
        "Zie [de code](de-code.md#het-datamodel), [privacy](../privacy.md) en [beheer](../beheer.md).\n"
    )
    PAGE = DocPage(
        "docs/handboek/x.md", "x.html", "X", link_base="https://github.com/o/r/blob/main/docs/handboek/", handboek=True
    )

    def test_every_section_gets_a_unique_ascii_anchor(self):
        sections = _sections(_markdown().parse(self.SOURCE))
        assert [anchor for anchor, _title in sections] == ["data-privacy-meer", "een-keer", "een-keer-2"]

    def test_sections_are_anchored_and_the_menu_is_included(self):
        html = render_doc_template(self.SOURCE, self.PAGE)
        assert '<h2 id="een-keer-2">' in html
        assert '{% include "parts/handboek_sidebar.html" %}' in html
        # The inline copy for narrow screens comes right after the title.
        assert html.index("</h1>") < html.index("handboek_menu_inline.html") < html.index("Intro.")

    def test_links_to_documents_wies_shows_stay_inside_wies(self):
        html = render_doc_template(self.SOURCE, self.PAGE)
        assert "href=\"{{ url('handboek-page', args=['de-code']) }}#het-datamodel\"" in html
        assert "href=\"{{ url('privacy') }}\"" in html
        # Not a page of its own in Wies: it goes to GitHub.
        assert 'href="https://github.com/o/r/blob/main/docs/handboek/../beheer.md"' in html

    def test_svg_image_is_inlined_from_the_template_dir(self):
        source = "![Plattegrond](../../wies/core/jinja2/handboek/img/architectuur.svg)\n"
        html = render_doc_template(source, self.PAGE)
        assert '{% include "handboek/img/architectuur.svg" %}' in html

    def test_other_images_are_refused(self):
        with pytest.raises(CommandError, match="SVG"):
            render_doc_template("![x](foto.png)\n", self.PAGE)

    def test_other_pages_get_no_menu_or_anchors(self):
        html = render_doc_template(self.SOURCE, DocPage("x.md", "x.html", "X"))
        assert "sidebar" not in html
        assert "<h2>Data, privacy &amp; meer</h2>" in html


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
    """Fails if docs/privacy.md, docs/handboek.md or SECURITY.md was edited without regenerating its page."""

    def test_doc_pages_are_up_to_date(self):
        try:
            call_command("generate_docs_html", check=True)
        except CommandError as exc:
            self.fail(str(exc))
