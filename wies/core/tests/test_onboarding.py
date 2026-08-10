import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.context_processors import onboarding
from wies.core.models import Assignment, Colleague, Label, LabelCategory, Placement, Service, Skill

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
        assert "onboarding_assignments" in ctx

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
        # Header title; the body title is personalized so it doesn't duplicate.
        self.assertContains(response, "Welkom bij Wies")
        self.assertContains(response, "Hoi Tess!")
        # Welcome step explains the tabs and carries the RIG-only disclaimer.
        self.assertContains(response, "Wie zit waar?")
        self.assertContains(response, "Aanvragen")
        self.assertContains(response, "Rijks ICT Gilde (RIG)")
        # Profile step (labels) is present.
        self.assertContains(response, "Vul je profiel aan")
        # A non-placed user has welcome + profile = two steps, no third.
        self.assertContains(response, 'data-step="2"')
        self.assertNotContains(response, 'data-step="3"')

    def test_wizard_not_shown_after_completion(self):
        self.user.onboarding_completed_at = timezone.now()
        self.user.save(update_fields=["onboarding_completed_at"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, 'id="onboardingWizard"')


class OnboardingLabelSaveTest(TestCase):
    """De profielstap (labels) slaat op via de bare inline_edit_form-macro.

    Regressie: die macro zette geen concurrency-token, en de save-view telt een
    ontbrekend token als conflict — dus de gekozen labels landden nooit in het
    profiel. De macro moet nu een geldig token renderen dat de save accepteert.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="lbl@rijksoverheid.nl", first_name="Lena")
        self.colleague = Colleague.objects.create(
            user=self.user, name="Lena Label", email="lbl@rijksoverheid.nl", source="wies"
        )
        self.category = LabelCategory.objects.create(name="Merk")
        self.label = Label.objects.create(name="Gateway review", category=self.category)
        self.category2 = LabelCategory.objects.create(name="Expertise")
        self.label2 = Label.objects.create(name="Data engineering", category=self.category2)

    def _token_re(self):
        return re.compile(r'name="_concurrency_token"\s+value="([^"]*)"')

    def _token_for(self, category_id):
        from wies.core.editables.colleague import ColleagueEditables  # noqa: PLC0415 — test-local
        from wies.core.views import _concurrency_token  # noqa: PLC0415 — avoids import cycle at module load

        spec = ColleagueEditables.resolve_dynamic(f"labels_{category_id}")
        return _concurrency_token(ColleagueEditables, spec, self.colleague)

    def _post_labels(self, category_id, label_id, token):
        url = reverse("inline-edit", args=["colleague", self.colleague.public_id, f"labels_{category_id}"])
        return self.client.post(url, {"labels": str(label_id), "_concurrency_token": token})

    def test_labels_form_renders_a_valid_concurrency_token(self):
        self.client.force_login(self.user)
        html = self.client.get(reverse("home")).content.decode()
        match = self._token_re().search(html)
        assert match, "de onboarding-labels-form moet een _concurrency_token embedden"
        token = match.group(1)
        assert token, "het token mag niet leeg zijn"
        assert "{{" not in token, "het token mag geen ongerenderde Jinja-expressie zijn"

    def test_onboarding_label_choice_persists(self):
        self.client.force_login(self.user)
        # Het token hoort bij dít categorieveld: de render bevat er meerdere
        # (merk, en één per labelcategorie), dus het eerste token uit de HTML
        # pakken zou het verkeerde veld treffen en de save als conflict weigeren.
        token = self._token_for(self.category.id)

        # De widget rendert name="labels", zoals de browser die post.
        response = self._post_labels(self.category.id, self.label.public_id, token)
        assert response.status_code == 200
        self.colleague.refresh_from_db()
        assert list(self.colleague.labels.values_list("id", flat=True)) == [self.label.id]

    def test_missing_token_is_rejected_as_conflict(self):
        # Bewijst dat het token de blokker was: zonder token slaat niets op.
        self.client.force_login(self.user)
        url = reverse("inline-edit", args=["colleague", self.colleague.public_id, f"labels_{self.category.id}"])
        self.client.post(url, {"labels": str(self.label.public_id)})
        self.colleague.refresh_from_db()
        assert list(self.colleague.labels.all()) == []

    def test_multiple_categories_all_persist(self):
        """De onboarding submit elke categorie serieel met het token dat op de
        LEGE begintoestand is berekend. Het per-``labels_<cat>``-token mag alleen
        die categorie hashen, anders maakt de eerste save de tokens van de andere
        categorieën stale → conflict → maar één categorie werd bewaard.
        """
        self.client.force_login(self.user)
        token1 = self._token_for(self.category.id)
        token2 = self._token_for(self.category2.id)

        r1 = self._post_labels(self.category.id, self.label.public_id, token1)
        # token2 is nog op de begintoestand berekend, net als in de wizard: een
        # save in categorie 1 mag hem niet ongeldig maken.
        r2 = self._post_labels(self.category2.id, self.label2.public_id, token2)

        assert r1.status_code == 200
        assert r2.status_code == 200
        self.colleague.refresh_from_db()
        assert set(self.colleague.labels.values_list("id", flat=True)) == {self.label.id, self.label2.id}

    def test_token_is_per_category(self):
        # Een label in categorie 1 mag het token van categorie 2 niet veranderen.
        self.colleague.labels.add(self.label)
        assert self._token_for(self.category.id) != self._token_for(self.category2.id)


class OnboardingAssignmentStepTest(TestCase):
    """Step 3 — the consultant checks their own opdracht(en)."""

    def setUp(self):
        self.client = Client()
        # BM/owner (the contact person when a field is read-only).
        self.bm_user = User.objects.create_user(email="bm@rijksoverheid.nl", first_name="Bea", last_name="Manager")
        self.bm = Colleague.objects.create(
            user=self.bm_user, name="Bea Manager", email="bm@rijksoverheid.nl", source="wies"
        )
        # The placed user going through onboarding. No Consultant group is
        # required — anyone with an active placement sees the step.
        self.user = User.objects.create_user(email="con@rijksoverheid.nl", first_name="Cas")
        self.colleague = Colleague.objects.create(
            user=self.user, name="Cas Consultant", email="con@rijksoverheid.nl", source="wies"
        )
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
        # The user's own service (rol) is attached for the rol/rolomschrijving rows.
        assert [s.skill_id for s in entries[0]["services"]] == [self.skill.id]
        # Owner mailto points at the BM's email, without a pre-filled body.
        assert entries[0]["owner_mailto"].startswith("mailto:bm@rijksoverheid.nl")
        assert "&body=" not in entries[0]["owner_mailto"]

    def test_context_empty_when_not_placed(self):
        ctx = onboarding(_request_for(self.user))
        assert ctx["onboarding_assignments"] == []

    def test_context_includes_external_sourced(self):
        # External (OTYS) opdrachten are shown too, matching the profile's
        # active list; their fields are read-only via the permission rules.
        assignment = self._place_on(source="otys_iir")
        ctx = onboarding(_request_for(self.user))
        assert [e["assignment"].id for e in ctx["onboarding_assignments"]] == [assignment.id]

    def test_wizard_renders_opdracht_step_and_bm_contact(self):
        assignment = self._place_on(name="Datateam MinBZK", description="Data engineering")
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "Controleer je opdracht")
        self.assertContains(response, "Datateam MinBZK")
        # De stap toont de gegevens; wijzigen gebeurt in het bewerkscherm.
        self.assertContains(response, "Wijzigen")
        self.assertContains(response, reverse("onboarding-assignment-edit", args=[assignment.public_id]))
        # The consultant's own rol + rolomschrijving are shown.
        self.assertContains(response, "Jouw rol")
        self.assertContains(response, "Data engineering")
        # BM is named and mailable.
        self.assertContains(response, "Bea Manager")
        self.assertContains(response, "mailto:bm@rijksoverheid.nl")
        # Welcome + profile + opdracht = three steps.
        self.assertContains(response, 'data-step="3"')

    def test_assignment_edit_screen_renders_and_saves(self):
        assignment = self._place_on(name="Datateam MinBZK", description="Data engineering")
        self.client.force_login(self.user)
        url = reverse("onboarding-assignment-edit", args=[assignment.public_id])

        response = self.client.get(url)
        assert response.status_code == 200
        self.assertContains(response, "Opdracht wijzigen")
        self.assertContains(response, "Datateam MinBZK")
        # Opdrachtvelden en de eigen rol staan in één formulier, elk met prefix.
        self.assertContains(response, "opdracht-name")
        self.assertContains(response, "Opdrachtomschrijving")

        service = assignment.services.first()
        response = self.client.post(
            url,
            {
                "opdracht-name": "Datateam BZK",
                "opdracht-extra_info": "Nieuwe omschrijving",
                f"rol-{service.id}-description": "Data engineering plus",
            },
        )
        assert response.status_code == 200
        # De bijgewerkte box gaat terug naar de stap; het scherm sluit zichzelf.
        assert response["HX-Retarget"] == f"#onboarding-assignment-{assignment.public_id}"
        assert response["HX-Trigger"] == "onboardingDetailClose"
        assignment.refresh_from_db()
        service.refresh_from_db()
        assert assignment.name == "Datateam BZK"
        assert assignment.extra_info == "Nieuwe omschrijving"
        assert service.description == "Data engineering plus"

    def test_assignment_edit_screen_rejects_other_assignment(self):
        # Een opdracht waar je niet op staat hoort niet bewerkbaar te zijn.
        other = Assignment.objects.create(name="Niet van mij", owner=self.bm, source="wies")
        self.client.force_login(self.user)
        response = self.client.get(reverse("onboarding-assignment-edit", args=[other.public_id]))
        assert response.status_code == 404

    def test_wizard_skips_opdracht_step_when_not_placed(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, "Controleer je opdracht")
        # No opdracht step → welcome + profile only, no third step.
        self.assertNotContains(response, 'data-step="3"')

    def test_step_shown_for_placed_user_without_consultant_group(self):
        # A placed user who is NOT in the Consultant group (e.g. bedrijfsvoering
        # or OR modelled via an ODI opdracht) still gets the opdracht-check step.
        self.user.groups.clear()
        self._place_on()
        ctx = onboarding(_request_for(self.user))
        assert len(ctx["onboarding_assignments"]) == 1
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Controleer je opdracht")


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
