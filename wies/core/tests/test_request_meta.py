from django.test import RequestFactory, TestCase, override_settings

from wies.core.models import Event
from wies.core.request_meta import (
    _get_client_ip,
    _get_user_agent,
    _valid_ip,
    get_request_metadata,
)
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
        assert _get_client_ip(request) == "10.0.0.5"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_hops_one_takes_rightmost_trusted_entry(self):
        """With one trusted hop, read the rightmost entry (the proxy added it), not the leftmost client value."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            REMOTE_ADDR="10.0.0.5",
        )
        assert _get_client_ip(request) == "2.2.2.2"

    @override_settings(TRUSTED_PROXY_HOPS=2)
    def test_hops_two_takes_second_from_right(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2, 3.3.3.3",
        )
        assert _get_client_ip(request) == "2.2.2.2"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_missing_header_falls_back_to_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.9")
        assert _get_client_ip(request) == "10.0.0.9"

    @override_settings(TRUSTED_PROXY_HOPS=2)
    def test_header_shorter_than_hops_falls_back(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1",
            REMOTE_ADDR="10.0.0.9",
        )
        assert _get_client_ip(request) == "10.0.0.9"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_result_is_validated_bare_ip(self):
        """The extractor sanitises the chosen hop itself: a port-suffixed entry
        yields the bare address, not the host:port string."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2:56789",
            REMOTE_ADDR="10.0.0.5",
        )
        assert _get_client_ip(request) == "2.2.2.2"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_best_effort_never_raises(self):
        """A broken request-like object must yield "" rather than raising."""
        assert _get_client_ip(_BrokenRequest()) == ""


class GetUserAgentTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_user_agent(self):
        request = self.factory.get("/", HTTP_USER_AGENT="Mozilla/5.0 test")
        assert _get_user_agent(request) == "Mozilla/5.0 test"

    def test_truncates_to_512(self):
        request = self.factory.get("/", HTTP_USER_AGENT="x" * 1000)
        assert len(_get_user_agent(request)) == 512

    def test_missing_returns_empty(self):
        request = self.factory.get("/")
        assert _get_user_agent(request) == ""


class ValidIpTest(TestCase):
    def test_passes_valid_ipv4_and_ipv6(self):
        assert _valid_ip("1.2.3.4") == "1.2.3.4"
        # IPv6 is returned in its normalised (compressed) form.
        assert _valid_ip("2001:0db8:0000:0000:0000:0000:0000:0001") == "2001:db8::1"
        assert _valid_ip("::1") == "::1"

    def test_strips_port_and_brackets_keeping_the_address(self):
        assert _valid_ip("1.2.3.4:56789") == "1.2.3.4"  # some load balancers add a port
        assert _valid_ip("[::1]:443") == "::1"
        assert _valid_ip("[2001:db8::1]") == "2001:db8::1"
        assert _valid_ip(" 1.2.3.4 ") == "1.2.3.4"  # surrounding whitespace tolerated

    def test_rejects_non_ip_values(self):
        assert _valid_ip("unknown") == ""
        assert _valid_ip("") == ""
        assert _valid_ip("1.2.3.4:56789:99") == ""  # not a recoverable host:port


class GetRequestMetadataTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_returns_all_four_values(self):
        """ip is derived (trusted hop), forwarded_for is the raw header, remote_addr is REMOTE_ADDR."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            HTTP_USER_AGENT="Mozilla/5.0 test",
            REMOTE_ADDR="10.0.0.5",
        )
        assert get_request_metadata(request) == {
            "ip": "2.2.2.2",  # derived, one trusted hop
            "forwarded_for": "1.1.1.1, 2.2.2.2",  # raw, unprocessed
            "remote_addr": "10.0.0.5",  # TCP peer
            "user_agent": "Mozilla/5.0 test",
        }

    def test_none_request_yields_empty_values(self):
        assert get_request_metadata(None) == {
            "ip": None,
            "forwarded_for": "",
            "remote_addr": None,
            "user_agent": "",
        }

    def test_forwarded_for_truncated_to_512(self):
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="x" * 1000)
        assert len(get_request_metadata(request)["forwarded_for"]) == 512

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_best_effort_never_raises(self):
        """A broken request-like object must yield empty/None, not raise."""
        assert get_request_metadata(_BrokenRequest()) == {
            "ip": None,
            "forwarded_for": "",
            "remote_addr": None,
            "user_agent": "",
        }


class CreateEventRequestMetaTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_request_metadata_populated_from_request(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
            HTTP_USER_AGENT="Mozilla/5.0 test",
            REMOTE_ADDR="10.0.0.5",
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
        assert event.forwarded_for == "1.1.1.1, 2.2.2.2"
        assert event.remote_addr == "10.0.0.5"
        assert event.user_agent == "Mozilla/5.0 test"
        assert "ip" not in event.context
        assert "user_agent" not in event.context

    def test_no_request_leaves_columns_empty(self):
        create_event(object_type="User", action="create", source="sync", object_id=1)
        event = Event.objects.get()
        assert event.ip is None
        assert event.forwarded_for == ""
        assert event.remote_addr is None
        assert event.user_agent == ""

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_best_effort_failure_still_writes_event(self):
        """If metadata extraction blows up, the event must still be recorded."""
        create_event(
            object_type="User",
            action="create",
            source="user",
            object_id=1,
            request=_BrokenRequest(),
        )
        event = Event.objects.get()
        assert event.forwarded_for == ""
        assert event.remote_addr is None
        assert event.user_agent == ""

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_ip_with_port_still_writes_event(self):
        """An X-Forwarded-For entry carrying a port (as some load balancers emit)
        must not break event creation.

        Extraction is best-effort but the value flows on into a
        GenericIPAddressField (Postgres inet), so an un-sanitised host:port value
        would raise a DataError on INSERT. Because create_event is called inside
        transaction.atomic() by the inline-edit path, that rollback would undo
        the user's own save — a failed audit attempt destroying the action.
        The port is stripped, so the address is kept rather than lost.
        """
        request = self.factory.get(
            "/",
            # rightmost trusted hop is "1.2.3.4:56789" — valid host:port, invalid inet
            HTTP_X_FORWARDED_FOR="9.9.9.9, 1.2.3.4:56789",
            REMOTE_ADDR="10.0.0.5",
        )
        create_event(
            object_type="User",
            action="create",
            source="user",
            object_id=1,
            request=request,
        )
        # The write succeeds; the port is stripped so the address survives, and
        # the raw header is still preserved verbatim as evidence.
        event = Event.objects.get()
        assert event.ip == "1.2.3.4"
        assert event.forwarded_for == "9.9.9.9, 1.2.3.4:56789"

    @override_settings(TRUSTED_PROXY_HOPS=0)
    def test_bracketed_remote_addr_still_writes_event(self):
        """A bracketed IPv6-with-port literal reaching remote_addr must likewise
        not break the write; the port is stripped and the address kept."""
        request = self.factory.get("/", REMOTE_ADDR="[::1]:443")
        create_event(
            object_type="User",
            action="create",
            source="user",
            object_id=1,
            request=request,
        )
        event = Event.objects.get()
        assert event.remote_addr == "::1"

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_unparseable_ip_dropped_but_event_written(self):
        """A value that is not a recoverable address at all is dropped to None,
        and the event is still recorded."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="9.9.9.9, unknown",
            REMOTE_ADDR="10.0.0.5",
        )
        create_event(
            object_type="User",
            action="create",
            source="user",
            object_id=1,
            request=request,
        )
        event = Event.objects.get()
        assert event.ip is None
        assert event.forwarded_for == "9.9.9.9, unknown"
