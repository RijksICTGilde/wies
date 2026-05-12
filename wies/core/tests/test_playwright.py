def test_playwright_loads_inline_html(page):
    page.set_content("<html><head><title>Example Domain</title></head><body><h1>OK</h1></body></html>")
    assert "Example" in page.title()
    assert page.locator("h1").inner_text() == "OK"
