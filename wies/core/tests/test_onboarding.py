from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.context_processors import onboarding
from wies.core.models import Assignment, Colleague, Placement, Service, Skill

User = get_user_model()


def _request_for(user):
    """Minimal request stand-in.

    The context processor reads ``request.user``; the owner-mailto helper also
    calls ``build_absolute_uri`` when an assignment has an owner with an email.
    """

    class _Req:
        def build_absolute_uri(self, location=""):
            return "http://testserver" + location

    req = _Req()
    req.user = user
    return req


class OnboardingModelTest(TestCase):
    def test_new_user_has_no_onboarding_timestamp(self):
        user = User.objects.create_user(email="new@rijksoverheid.nl")
        assert user.onboarding_completed_at is None


class OnboardingContextProcessorTest(TestCase):
    def setUp(self):
        self.factory_user = User.objects.create_user(email="ctx@rijksoverheid.nl")

    def test_show_onboarding_true_for_fresh_user(self):
        ctx = onboarding(_request_for(self.factory_user))
        assert ctx["show_onboarding"] is True
        assert "onboarding_label_categories" in ctx

    def test_show_onboarding_false_once_completed(self):
        self.factory_user.onboarding_completed_at = timezone.now()
        self.factory_user.save(update_fields=["onboarding_completed_at"])
        ctx = onboarding(_request_for(self.factory_user))
        assert ctx["show_onboarding"] is False

    def test_show_onboarding_false_for_anonymous(self):
        ctx = onboarding(_request_for(AnonymousUser()))
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
        # Five steps: welcome, profile, and three tour places.
        self.assertContains(response, 'data-step="5"')
        # Rijksprofiel link placeholder is present.
        self.assertContains(response, "Rijksprofiel koppelen")

    def test_wizard_not_shown_after_completion(self):
        self.user.onboarding_completed_at = timezone.now()
        self.user.save(update_fields=["onboarding_completed_at"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, 'id="onboardingWizard"')


class OnboardingAssignmentStepTest(TestCase):
    """Step 4 — the consultant checks their own opdracht(en)."""

    def setUp(self):
        self.client = Client()
        # BM/owner (the contact person when a field is read-only).
        self.bm_user = User.objects.create_user(email="bm@rijksoverheid.nl", first_name="Bea", last_name="Manager")
        self.bm = Colleague.objects.create(
            user=self.bm_user, name="Bea Manager", email="bm@rijksoverheid.nl", source="wies"
        )
        # The consultant going through onboarding (in the Consultant group —
        # the step is consultant-only).
        self.user = User.objects.create_user(email="con@rijksoverheid.nl", first_name="Cas")
        self.colleague = Colleague.objects.create(
            user=self.user, name="Cas Consultant", email="con@rijksoverheid.nl", source="wies"
        )
        self.user.groups.add(Group.objects.get_or_create(name="Consultant")[0])
        self.skill = Skill.objects.create(name="Rol")

    def _place_on(self, name="Mijn opdracht", *, source="wies", description="Dienst"):
        assignment = Assignment.objects.create(name=name, owner=self.bm, source=source)
        service = Service.objects.create(
            description=description, assignment=assignment, skill=self.skill, source="wies"
        )
        Placement.objects.create(colleague=self.colleague, service=service, source="wies")
        return assignment

    def test_context_lists_placed_assignment(self):
        assignment = self._place_on()
        ctx = onboarding(_request_for(self.user))
        entries = ctx["onboarding_assignments"]
        assert [e["assignment"].id for e in entries] == [assignment.id]
        # The consultant's own service (rol) is attached for the rol/rolomschrijving rows.
        assert [s.skill_id for s in entries[0]["services"]] == [self.skill.id]
        # Owner mailto is prefilled from the BM's email.
        assert entries[0]["owner_mailto"].startswith("mailto:bm@rijksoverheid.nl")

    def test_context_empty_when_not_placed(self):
        ctx = onboarding(_request_for(self.user))
        assert ctx["onboarding_assignments"] == []

    def test_context_excludes_non_wies_sourced(self):
        # An externally-sourced opdracht is not something the consultant edits here.
        self._place_on(source="otys_iir")
        ctx = onboarding(_request_for(self.user))
        assert ctx["onboarding_assignments"] == []

    def test_wizard_renders_opdracht_step_and_bm_contact(self):
        self._place_on(name="Datateam MinBZK", description="Data engineering")
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "Controleer je opdracht")
        self.assertContains(response, "Datateam MinBZK")
        # Placed consultant may edit name/omschrijving inline (pencil affordance).
        self.assertContains(response, "extra_info")
        # The consultant's own rol + rolomschrijving are shown.
        self.assertContains(response, "Jouw rol")
        self.assertContains(response, "Omschrijving rol")
        self.assertContains(response, "Data engineering")
        # BM is named and mailable.
        self.assertContains(response, "Bea Manager")
        self.assertContains(response, "mailto:bm@rijksoverheid.nl")
        # With an opdracht the wizard has six steps.
        self.assertContains(response, 'data-step="6"')

    def test_wizard_skips_opdracht_step_when_not_placed(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, "Controleer je opdracht")
        # No opdracht step → back to five steps, no sixth dot/panel.
        self.assertNotContains(response, 'data-step="6"')

    def test_step_hidden_for_non_consultant_even_when_placed(self):
        # A placed user who is NOT in the Consultant group (e.g. a BDM or
        # Beheerder) does not get the opdracht-check step.
        self.user.groups.clear()
        self._place_on()
        ctx = onboarding(_request_for(self.user))
        assert ctx["onboarding_assignments"] == []
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Controleer je opdracht")


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
