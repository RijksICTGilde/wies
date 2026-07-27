"""Tests for the create_auth_event service.

Mirrors wies/core/tests/test_request_meta.py::CreateEventRequestMetaTest for the
AuthEvent (login/logout) audit trail: proves the client IP + User-Agent are
recorded when a request is passed, and left empty when it is not.
"""

import pytest
from django.test import RequestFactory, TestCase, override_settings

from wies.rijksauth.models import AuthEvent
from wies.rijksauth.services.events import create_auth_event


class CreateAuthEventRequestMetaTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_ip_and_user_agent_populated_from_request(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            HTTP_USER_AGENT="Mozilla/5.0 test",
        )
        create_auth_event("u@rijksoverheid.nl", "Login.success", request=request)
        event = AuthEvent.objects.get()
        assert event.ip == "2.2.2.2"
        assert event.user_agent == "Mozilla/5.0 test"

    def test_no_request_leaves_ip_and_user_agent_empty(self):
        create_auth_event("u@rijksoverheid.nl", "Login.success")
        event = AuthEvent.objects.get()
        assert event.ip is None
        assert event.user_agent == ""

    def test_unsupported_event_name_raises(self):
        with pytest.raises(ValueError, match="Unsupported auth event"):
            create_auth_event("u@rijksoverheid.nl", "Nonsense")
