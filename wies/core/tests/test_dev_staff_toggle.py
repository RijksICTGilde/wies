"""The local-only staff switch in the user menu."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from wies.core.roles import is_staff_member, setup_roles
from wies.rijksauth.middleware import STAFF_OVERRIDE_SESSION_KEY

User = get_user_model()


class StaffOverrideTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.user = User.objects.create(email="dev@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.client.force_login(self.user)

    @override_settings(DEBUG=True, STAFF_EMAILS=[])
    def test_the_switch_grants_and_revokes_staff_for_the_session(self):
        assert not is_staff_member(self.user)
        response = self.client.post(reverse("dev-staff-toggle"), {"terug": "/profiel/"})
        assert response.status_code == 302
        assert response.url == "/profiel/"
        assert self.client.session[STAFF_OVERRIDE_SESSION_KEY] is True
        body = self.client.get("/profiel/").content.decode()
        assert "Staff-rechten aan voor deze sessie." in body

    @override_settings(DEBUG=True, STAFF_EMAILS=[])
    def test_the_middleware_carries_the_switch_onto_the_request(self):
        """The staff-only dashboard opens with the switch on and is refused with
        it off. A fresh client: the middleware chain is built on the first
        request, so the setting has to be in place before that."""
        with self.modify_settings(MIDDLEWARE={"append": "wies.rijksauth.middleware.StaffOverrideMiddleware"}):
            client = Client()
            client.force_login(self.user)
            session = client.session
            session[STAFF_OVERRIDE_SESSION_KEY] = True
            session.save()
            assert client.get(reverse("staff-dashboard")).status_code == 200
            client.post(reverse("dev-staff-toggle"))
            assert client.session[STAFF_OVERRIDE_SESSION_KEY] is False
            assert client.get(reverse("staff-dashboard")).status_code == 302

    @override_settings(DEBUG=True, STAFF_EMAILS=["dev@rijksoverheid.nl"])
    def test_the_switch_can_turn_a_real_staff_member_off(self):
        assert is_staff_member(self.user)
        self.user.wies_staff_override = False
        assert not is_staff_member(self.user)

    @override_settings(DEBUG=False, STAFF_EMAILS=[])
    def test_outside_debug_the_switch_does_not_exist(self):
        assert self.client.post(reverse("dev-staff-toggle")).status_code == 404
        self.user.wies_staff_override = True
        assert not is_staff_member(self.user)

    @override_settings(DEBUG=False)
    def test_the_menu_item_is_local_only(self):
        body = self.client.get(reverse("user-profile")).content.decode()
        assert "Staff-rechten" not in body
