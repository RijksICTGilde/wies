"""Tests for the create_event service.

Focused on proving core's audit `Event` records request metadata. The
`request_meta` helper itself lives in `wies.rijksauth.request_meta`; its unit
tests are in `wies/rijksauth/tests/test_request_meta.py`.
"""

from django.test import RequestFactory, TestCase, override_settings

from wies.core.models import Event
from wies.core.services.events import create_event

_BOOM = RuntimeError("boom")


class _BrokenMeta:
    """A request.META stand-in that raises on access — to prove extraction is best-effort."""

    def get(self, *args, **kwargs):
        raise _BOOM


class _BrokenRequest:
    META = _BrokenMeta()


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
