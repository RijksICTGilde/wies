from unittest.mock import patch

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
            assert nldd_asset("ndd.bundle.js").endswith("/vendor/nldd/ndd.bundle.js?v=1.2.3")

    def test_url_is_left_alone_without_a_version_file(self):
        # A checkout where build-nldd has not run yet: no query rather than an
        # empty one that would look like a real cache key.
        with patch("wies.core.services.version.Path.read_text", side_effect=OSError):
            assert nldd_asset("ndd.bundle.js").endswith("/vendor/nldd/ndd.bundle.js")

    def test_base_template_uses_the_versioned_url(self):
        response = Client().get("/geen-toegang/")
        assert b"ndd.bundle.js?v=" in response.content
        assert b"ndd.styles.css?v=" in response.content
