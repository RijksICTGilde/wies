import re
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import Client, TestCase

from config.jinja2 import nldd_asset
from wies.core.services.version import get_nldd_version


class NlddAssetTest(TestCase):
    """The vendor bundle keeps its name across upgrades, so the URL carries
    the design-system version to stop a browser reusing the previous one."""

    def setUp(self):
        get_nldd_version.cache_clear()

    def tearDown(self):
        get_nldd_version.cache_clear()

    def test_url_carries_the_built_version(self):
        with patch("wies.core.services.version.Path.read_text", return_value="@nldd/design-system 1.2.3\nbuilt x\n"):
            assert nldd_asset("nldd.min.js").endswith("/vendor/nldd/nldd.min.js?v=1.2.3")

    def test_url_is_left_alone_without_a_version_file(self):
        # A checkout where update-vendor has not run yet: no query rather than an
        # empty one that would look like a real cache key.
        with patch("wies.core.services.version.Path.read_text", side_effect=OSError):
            assert nldd_asset("nldd.min.js").endswith("/vendor/nldd/nldd.min.js")

    def test_base_template_uses_the_versioned_url(self):
        response = Client().get("/geen-toegang/")
        assert b"nldd.min.js?v=" in response.content
        assert b"css/global.css?v=" in response.content


class NlddVendorFilesTest(TestCase):
    """update-vendor drops the NLDD files Wies does not load. A missing import
    or font only shows as a 404 in the browser; this fails instead."""

    VENDOR = Path(settings.BASE_DIR) / "wies/core/static/vendor/nldd/css"

    def test_every_import_and_font_of_a_loaded_stylesheet_exists(self):
        pending = ["global.css", "rich-text.css"]
        seen = set()
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            path = self.VENDOR / name
            with self.subTest(stylesheet=name):
                assert path.is_file()
            if not path.is_file():
                continue
            css = path.read_text()
            pending.extend(re.findall(r"""@import\s+["']\./([^"']+)["']""", css))
            for ref in re.findall(r"""url\(["']?(\.\./fonts/[^"')]+)["']?\)""", css):
                with self.subTest(stylesheet=name, font=ref):
                    assert (self.VENDOR / ref).resolve().is_file()


class NlddInternalsTest(TestCase):
    """side_panel.js styles nldd-page from inside its shadow root, so it leans
    on an internal name. An upgrade that renames it would switch the fix off
    silently; this fails instead."""

    def test_bundle_still_has_the_names_the_scripts_use(self):
        bundle = (Path(settings.BASE_DIR) / "wies/core/static/vendor/nldd/nldd.min.js").read_text()
        assert "page__scroll" in bundle
