from django.test import RequestFactory, TestCase, override_settings

from wies.core.models import Event
from wies.core.request_meta import get_client_ip, get_user_agent
from wies.core.services.events import create_event

_BOOM = RuntimeError("boom")


class _BrokenMeta:
    """A request.META stand-in that raises on access — to prove extraction is best-effort."""

    def get(self, *args, **kwargs):
        raise _BOOM


class _BrokenRequest:
    META = _BrokenMeta()


class GetClientIpTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_HOPS=0)
    def test_hops_zero_ignores_forwarded_for(self):
        """With no trusted hops, a client-supplied X-Forwarded-For must not be honoured."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            REMOTE_ADDR="10.0.0.5",
        )
        assert get_client_ip(request) == "10.0.0.5"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_hops_one_takes_rightmost_trusted_entry(self):
        """With one trusted hop, read the rightmost entry (the proxy added it), not the leftmost client value."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            REMOTE_ADDR="10.0.0.5",
        )
        assert get_client_ip(request) == "2.2.2.2"

    @override_settings(TRUSTED_PROXY_HOPS=2)
    def test_hops_two_takes_second_from_right(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2, 3.3.3.3",
        )
        assert get_client_ip(request) == "2.2.2.2"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_missing_header_falls_back_to_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.9")
        assert get_client_ip(request) == "10.0.0.9"

    @override_settings(TRUSTED_PROXY_HOPS=2)
    def test_header_shorter_than_hops_falls_back(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1",
            REMOTE_ADDR="10.0.0.9",
        )
        assert get_client_ip(request) == "10.0.0.9"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_best_effort_never_raises(self):
        """A broken request-like object must yield "" rather than raising."""
        assert get_client_ip(_BrokenRequest()) == ""


class GetUserAgentTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_user_agent(self):
        request = self.factory.get("/", HTTP_USER_AGENT="Mozilla/5.0 test")
        assert get_user_agent(request) == "Mozilla/5.0 test"

    def test_truncates_to_512(self):
        request = self.factory.get("/", HTTP_USER_AGENT="x" * 1000)
        assert len(get_user_agent(request)) == 512

    def test_missing_returns_empty(self):
        request = self.factory.get("/")
        assert get_user_agent(request) == ""


class CreateEventRequestMetaTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_ip_and_user_agent_populated_from_request(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            HTTP_USER_AGENT="Mozilla/5.0 test",
        )
        create_event(
            object_type="User",
            action="create",
            source="user",
            object_id=1,
            request=request,
        )
        event = Event.objects.get()
        # Stored as dedicated columns, not in context.
        assert event.ip == "2.2.2.2"
        assert event.user_agent == "Mozilla/5.0 test"
        assert "ip" not in event.context
        assert "user_agent" not in event.context

    def test_no_request_leaves_columns_empty(self):
        create_event(object_type="User", action="create", source="sync", object_id=1)
        event = Event.objects.get()
        assert event.ip is None
        assert event.user_agent == ""

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_best_effort_failure_still_writes_event(self):
        """If IP/UA extraction blows up, the event must still be recorded."""
        create_event(
            object_type="User",
            action="create",
            source="user",
            object_id=1,
            request=_BrokenRequest(),
        )
        event = Event.objects.get()
        assert event.ip is None
        assert event.user_agent == ""
