"""Every save and delete confirms itself with a notification.

The message text is what the notification shows and what live_region.js reads
out; the merk list partial has to carry the flash block itself because that
save does not reload the page.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    Suborganization,
)
from wies.core.tests.role_helpers import grant_bdm

User = get_user_model()

HX = {"HTTP_HX_REQUEST": "true"}


def last_message(response):
    # Messages queue up in the session until a page renders them, and these
    # responses render none, so an earlier one is still there: the newest counts.
    return [str(m) for m in get_messages(response.wsgi_request)][-1]


class SuccessMessageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="beheer@rijksoverheid.nl", first_name="Be", last_name="Heerder")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "add_user",
                    "change_user",
                    "delete_user",
                    "view_user",
                    "add_label",
                    "change_label",
                    "delete_label",
                    "change_labelcategory",
                    "add_suborganization",
                    "change_suborganization",
                    "delete_suborganization",
                ]
            )
        )
        self.client.force_login(self.user)

    def test_user_create_edit_delete(self):
        data = {"first_name": "Jan", "last_name": "Jansen", "email": "jan@rijksoverheid.nl"}
        response = self.client.post(reverse("user-create"), data, **HX)
        assert response.status_code == 200
        assert last_message(response) == "Gebruiker Jan Jansen is toegevoegd."

        jan = User.objects.get(email="jan@rijksoverheid.nl")
        response = self.client.post(reverse("user-edit", args=[jan.public_id]), {**data, "last_name": "Jans"}, **HX)
        assert last_message(response) == "Gebruiker Jan Jans is opgeslagen."

        response = self.client.post(reverse("user-delete", args=[jan.public_id]), **HX)
        assert last_message(response) == "Gebruiker Jan Jans is verwijderd."

    def test_profile_name_and_labels(self):
        response = self.client.post(reverse("profile-name-edit"), {"first_name": "Be", "last_name": "Heerder"}, **HX)
        assert last_message(response) == "Je naam is opgeslagen."
        response = self.client.post(reverse("profile-labels-edit"), {}, **HX)
        assert last_message(response) == "Je labels zijn opgeslagen."

    def test_label_add_edit_delete(self):
        category = LabelCategory.objects.create(name="Thema", color="#0066CC")
        response = self.client.post(reverse("label-form-create"), {"category": category.pk, "name": "Python"}, **HX)
        assert last_message(response) == 'Label "Python" is toegevoegd.'
        label = Label.objects.get(name="Python")
        response = self.client.post(
            reverse("label-form-edit", args=[label.public_id]), {"category": category.pk, "name": "Django"}, **HX
        )
        assert last_message(response) == 'Label "Django" is opgeslagen.'
        response = self.client.post(reverse("label-delete", args=[label.public_id]), **HX)
        assert last_message(response) == 'Label "Django" is verwijderd.'

    def test_suborganization_add_carries_the_banner_in_the_partial(self):
        response = self.client.post(reverse("suborganization-create"), {"name": "Merk A"}, **HX)
        assert response.status_code == 200
        self.assertContains(response, 'id="flash-messages"')
        self.assertContains(response, 'hx-swap-oob="outerHTML"')
        self.assertContains(response, 'text="Merk &#34;Merk A&#34; is toegevoegd."')

    def test_suborganization_edit_and_delete(self):
        merk = Suborganization.objects.create(name="Merk B")
        response = self.client.post(reverse("suborganization-edit", args=[merk.public_id]), {"name": "Merk C"}, **HX)
        self.assertContains(response, 'text="Merk &#34;Merk C&#34; is opgeslagen."')
        response = self.client.post(reverse("suborganization-delete", args=[merk.public_id]), **HX)
        assert last_message(response) == 'Merk "Merk C" is verwijderd.'

    def test_placement_save_shows_the_banner_in_the_panel_it_returns_to(self):
        owner_user = grant_bdm(
            User.objects.create_user(email="owner@rijksoverheid.nl", first_name="Oma", last_name="Eigenaar")
        )
        self.client.force_login(owner_user)
        owner = Colleague.objects.get(user=owner_user)
        assignment = Assignment.objects.create(
            name="Aanvraag", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31), source="wies", owner=owner
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Rol",
            skill=Skill.objects.create(name="Dev"),
            status="OPEN",
            source="wies",
        )
        placement = Placement.objects.create(colleague=owner, service=service, source="wies")
        payload = {
            "skill": str(service.skill.public_id),
            "description": "Rol met nieuwe omschrijving",
            "period_source": Placement.SERVICE,
            "terug_url": f"/?plaatsing={placement.public_id}",
        }
        response = self.client.post(reverse("placement-edit", args=[placement.public_id]), payload, **HX)
        assert response.status_code == 204, response.content

        # What HX-Location fetches next: the placement panel, with the banner out
        # of band. Not read through last_message() first: reading marks a message
        # used, and then the next request would not carry it any more.
        panel = self.client.get(f"/?plaatsing={placement.public_id}", HTTP_HX_TARGET="side-panel-content", **HX)
        assert panel.status_code == 200
        self.assertContains(panel, 'hx-swap-oob="outerHTML"')
        self.assertContains(panel, f'text="Plaatsing van {owner.name} is opgeslagen."')

    def test_team_member_delete(self):
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=["change_assignment", "delete_service"]))
        org = OrganizationUnit.objects.create(name="Org", label="Org")
        assignment = Assignment.objects.create(
            name="Aanvraag",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
            source="wies",
            owner=self.user.colleague,
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        service = Service.objects.create(
            assignment=assignment,
            description="Rol",
            skill=Skill.objects.create(name="Dev"),
            status="OPEN",
            source="wies",
        )
        response = self.client.post(
            reverse("assignment-member-delete", args=[assignment.public_id, service.public_id]), **HX
        )
        assert response.status_code == 204, response.content
        assert last_message(response) == "Teamlid is verwijderd."
