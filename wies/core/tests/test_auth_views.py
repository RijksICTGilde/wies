from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

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
