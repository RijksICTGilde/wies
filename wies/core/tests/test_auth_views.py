import importlib
import os
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from config.settings import base
from wies.core.services.users import is_allowed_email_domain

User = get_user_model()


class NoAccessViewTest(TestCase):
    """Tests for the no-access page (Wies-specific, stays in core)"""

    def setUp(self):
        self.client = Client()

    def test_no_access_page_with_non_odi_email(self):
        """Test no_access page shows correct message for non-ODI email"""
        # Set up session with non-ODI email
        session = self.client.session
        session["failed_login_email"] = "user@external.com"
        session.save()

        response = self.client.get("/geen-toegang/")

        assert response.status_code == 200
        self.assertContains(response, "user@external.com")
        self.assertContains(response, "ODI / BZK e-mailadres")
        # Should show the "wrong account" scenario
        self.assertContains(response, "opdrachtgever")

    def test_no_access_page_with_odi_email(self):
        """Test no_access page shows correct message for ODI email without access"""
        # Set up session with ODI email
        session = self.client.session
        session["failed_login_email"] = "user@rijksoverheid.nl"
        session.save()

        response = self.client.get("/geen-toegang/")

        assert response.status_code == 200
        self.assertContains(response, "user@rijksoverheid.nl")
        # Should show the "request access" scenario
        self.assertContains(response, "nog geen toegang")
        self.assertContains(response, "wies-odi@rijksoverheid.nl")

    def test_no_access_page_clears_email_from_session(self):
        """Test that viewing no_access page clears email from session"""
        session = self.client.session
        session["failed_login_email"] = "user@external.com"
        session.save()

        self.client.get("/geen-toegang/")

        # Email should be cleared from session after viewing
        assert self.client.session.get("failed_login_email") is None

    def test_no_access_page_without_email(self):
        """Test no_access page works without email in session"""
        response = self.client.get("/geen-toegang/")

        assert response.status_code == 200
        # Should show generic message without specific email
        self.assertContains(response, "ODI / BZK e-mailadres")

    def test_allowed_email_domains_setting(self):
        """Test that ALLOWED_EMAIL_DOMAINS setting contains expected domains"""
        assert "@rijksoverheid.nl" in settings.ALLOWED_EMAIL_DOMAINS
        assert "@minbzk.nl" in settings.ALLOWED_EMAIL_DOMAINS

    @override_settings(ALLOWED_EMAIL_DOMAINS=["@rijksoverheid.nl", "@minfin.nl"])
    def test_no_access_page_names_the_configured_domains(self):
        response = self.client.get("/geen-toegang/")

        self.assertContains(response, "@rijksoverheid.nl, @minfin.nl")


class AllowedEmailDomainsSettingTest(SimpleTestCase):
    """``settings.ALLOWED_EMAIL_DOMAINS`` in ``config/settings/base.py``.

    Reloading the module re-runs the assignment; ``django.conf.settings`` copied
    its values at startup, so the reload cannot leak into other tests.
    """

    def _domains_with(self, value):
        with patch.dict(os.environ, {"ALLOWED_EMAIL_DOMAINS": value}):
            return importlib.reload(base).ALLOWED_EMAIL_DOMAINS

    def test_unset_or_empty_gives_the_default(self):
        """Never []: an empty list switches the domain check off."""
        for value in ("", " , ", "@"):
            with self.subTest(value=value):
                assert self._domains_with(value) == ["@rijksoverheid.nl", "@minbzk.nl"]

    def test_domains_are_split_trimmed_lowercased_and_prefixed(self):
        domains = self._domains_with(" @Rijksoverheid.nl , minfin.nl,, @MinBZK.nl ")

        assert domains == ["@rijksoverheid.nl", "@minfin.nl", "@minbzk.nl"]


class AllowedEmailDomainCheckTest(SimpleTestCase):
    @override_settings(ALLOWED_EMAIL_DOMAINS=["@rijksoverheid.nl", "@minfin.nl"])
    def test_configured_domains_are_allowed(self):
        assert is_allowed_email_domain("Pen.Tester@MinFin.nl")
        assert is_allowed_email_domain("iemand@rijksoverheid.nl")

    @override_settings(ALLOWED_EMAIL_DOMAINS=["@rijksoverheid.nl", "@minfin.nl"])
    def test_other_domains_are_refused(self):
        assert not is_allowed_email_domain("iemand@minbzk.nl")
        assert not is_allowed_email_domain("iemand@notminfin.nl")
