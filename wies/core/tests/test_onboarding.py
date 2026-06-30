from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.context_processors import onboarding

User = get_user_model()


class OnboardingModelTest(TestCase):
    def test_new_user_has_no_onboarding_timestamp(self):
        user = User.objects.create_user(email="new@rijksoverheid.nl")
        assert user.onboarding_completed_at is None


class OnboardingContextProcessorTest(TestCase):
    def setUp(self):
        self.factory_user = User.objects.create_user(email="ctx@rijksoverheid.nl")

    def _request_for(self, user):
        # The context processor only reads request.user.
        class _Req:
            pass

        req = _Req()
        req.user = user
        return req

    def test_show_onboarding_true_for_fresh_user(self):
        ctx = onboarding(self._request_for(self.factory_user))
        assert ctx["show_onboarding"] is True
        assert "onboarding_label_categories" in ctx

    def test_show_onboarding_false_once_completed(self):
        self.factory_user.onboarding_completed_at = timezone.now()
        self.factory_user.save(update_fields=["onboarding_completed_at"])
        ctx = onboarding(self._request_for(self.factory_user))
        assert ctx["show_onboarding"] is False

    def test_show_onboarding_false_for_anonymous(self):
        ctx = onboarding(self._request_for(AnonymousUser()))
        assert ctx["show_onboarding"] is False


class OnboardingWizardRenderTest(TestCase):
    """The wizard is injected by base.html on every page for a fresh user."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="wizard@rijksoverheid.nl", first_name="Tess")

    def test_wizard_shown_on_home_for_fresh_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, 'id="onboardingWizard"')
        self.assertContains(response, "Welkom bij Wies")

    def test_wizard_not_shown_after_completion(self):
        self.user.onboarding_completed_at = timezone.now()
        self.user.save(update_fields=["onboarding_completed_at"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, 'id="onboardingWizard"')


class OnboardingCompleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="finish@rijksoverheid.nl")

    def test_post_marks_completed_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("onboarding-complete"))
        assert response.status_code == 302
        self.user.refresh_from_db()
        assert self.user.onboarding_completed_at is not None

    def test_htmx_post_returns_close_trigger(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("onboarding-complete"), headers={"HX-Request": "true"})
        assert response.status_code == 204
        assert response.headers.get("HX-Trigger") == "closeOnboarding"
        self.user.refresh_from_db()
        assert self.user.onboarding_completed_at is not None

    def test_completion_is_idempotent(self):
        first = timezone.now()
        self.user.onboarding_completed_at = first
        self.user.save(update_fields=["onboarding_completed_at"])
        self.client.force_login(self.user)
        self.client.post(reverse("onboarding-complete"))
        self.user.refresh_from_db()
        # Existing timestamp must not be overwritten.
        assert self.user.onboarding_completed_at == first

    def test_get_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("onboarding-complete"))
        assert response.status_code == 405
