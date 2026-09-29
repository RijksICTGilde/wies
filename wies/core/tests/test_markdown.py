"""The description renderer: Markdown in, safe HTML out, plain text unharmed."""

from django.test import SimpleTestCase
from markupsafe import Markup

from wies.core.services.markdown import markdown_excerpt, markdown_text, render_markdown


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
        html = render_markdown("**vet** en *cursief*\n\n- een\n- twee")
        assert "<strong>vet</strong>" in html
        assert "<em>cursief</em>" in html
        assert "<ul>" in html
        assert "<li>een</li>" in html

    def test_headings_render_two_levels_down(self):
        html = render_markdown("# Kop\n\n## Subkop\n\n##### Diep")
        assert "<h3>Kop</h3>" in html
        assert "<h4>Subkop</h4>" in html
        assert "<h6>Diep</h6>" in html
        assert "<h1>" not in html

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
        assert 'style="' not in html
        assert "&lt;script&gt;" in html

    def test_images_stay_text(self):
        html = render_markdown("![alt](https://example.org/x.png)")
        assert "<img" not in html

    def test_links_open_beside_wies(self):
        html = render_markdown("[Wies](https://example.org/)")
        assert '<a href="https://example.org/" target="_blank" rel="noopener">Wies</a>' in html

    def test_a_link_without_scheme_gets_https(self):
        # Otherwise the browser resolves "google.com" under the current page.
        html = render_markdown("[zoek](google.com) en [hier](/opdrachten/) en [mail](mailto:a@b.nl)")
        assert 'href="https://google.com"' in html
        assert 'href="/opdrachten/"' in html
        assert 'href="mailto:a@b.nl"' in html

    def test_a_lone_asterisk_stays(self):
        html = render_markdown("2 * 3 = 6")
        assert "2 * 3 = 6" in html

    def test_output_is_markup(self):
        assert isinstance(render_markdown("x"), Markup)


class MarkdownExcerptTest(SimpleTestCase):
    def test_plain_text_drops_the_formatting(self):
        assert markdown_text("# Kop\n\n**vet** en [link](https://x.nl)\n\n- een\n- twee") == "Kop vet en link een twee"

    def test_excerpt_is_the_first_sentence(self):
        assert markdown_excerpt("Eerste zin. Tweede zin!") == "Eerste zin."
        assert markdown_excerpt("Alleen dit") == "Alleen dit"
        assert markdown_excerpt("") == ""

    def test_a_long_first_sentence_is_cut(self):
        assert markdown_excerpt("x" * 300, limit=20) == "x" * 19 + "…"
