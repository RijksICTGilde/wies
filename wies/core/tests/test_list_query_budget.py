"""Each request a list page makes does only the work its response needs.

The four faceted lists answer five kinds of request: the full page, a filter
change, the next page of rows ("Meer tonen"), the full option list of one
filter group ("Meer…") and the side panel. These tests pin that a lighter
request stays lighter, and that no request costs more queries as the list
grows (no N+1 per card or row).
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from wies.core.models import (
    Assignment,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    Suborganization,
)
from wies.core.roles import ROLE_BUSINESS_MANAGER, ROLE_CONSULTANT, ROLE_USER_ADMIN, setup_roles

User = get_user_model()

HX = {"HX-Request": "true"}
PANEL = {"HX-Request": "true", "HX-Target": "side-panel-content"}


class ListQueryBudgetTest(TestCase):
    def setUp(self):
        setup_roles()
        self.user = User.objects.create(email="bm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        for role in (ROLE_BUSINESS_MANAGER, ROLE_USER_ADMIN):
            self.user.groups.add(Group.objects.get(name=role))
        self.client = Client()
        self.client.force_login(self.user)

        self.skill = Skill.objects.create(name="Ontwikkelaar")
        self.thema = LabelCategory.objects.create(name="Thema", color="#0066CC")
        self.niveau = LabelCategory.objects.create(name="Niveau", color="#00AA00")
        self.label_thema = Label.objects.create(name="AI", category=self.thema)
        self.label_niveau = Label.objects.create(name="Senior", category=self.niveau)
        self.suborg = Suborganization.objects.create(name="Digi Gilde")
        self.org = OrganizationUnit.objects.create(name="Ministerie van Testzaken", label="TZ")
        self.consultant_group = Group.objects.get(name=ROLE_CONSULTANT)
        self.made = 0

    def _grow(self, count):
        """``count`` more consultants, each placed on an opdracht of their own and
        one open aanvraag beside it."""
        today = timezone.now().date()
        for _ in range(count):
            i = self.made = self.made + 1
            user = User.objects.create(email=f"c{i}@rijksoverheid.nl", first_name="C", last_name=f"{i:03d}")
            user.groups.add(self.consultant_group)
            colleague = Colleague.objects.get_or_create(
                email=user.email, defaults={"name": f"Collega {i:03d}", "source": "wies"}
            )[0]
            colleague.user = user
            colleague.suborganization = self.suborg
            colleague.save()
            colleague.labels.add(self.label_thema, self.label_niveau)
            assignment = Assignment.objects.create(
                name=f"Opdracht {i:03d}",
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=30),
                source="wies",
            )
            assignment.organizations.add(self.org)
            service = Service.objects.create(assignment=assignment, description="Rol", skill=self.skill, source="wies")
            Placement.objects.create(colleague=colleague, service=service, source="wies")
            Service.objects.create(
                assignment=assignment, description="Open", skill=self.skill, status="OPEN", source="wies"
            )
        self.colleague = Colleague.objects.order_by("id").first()
        self.assignment = Assignment.objects.order_by("id").first()

    def _queries(self, url, params=None, headers=None):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url, params or {}, headers=headers or {})
        assert response.status_code == 200, (url, params, response.status_code)
        return len(queries)

    def _filters(self):
        return {
            "rol": str(self.skill.public_id),
            "labels": [str(self.label_thema.public_id), str(self.label_niveau.public_id)],
            "org": str(self.org.public_id),
        }

    def _request_kinds(self, url, filters):
        return {
            "full": self._queries(url, filters),
            "filter change": self._queries(url, filters, HX),
            "next page": self._queries(url, {**filters, "pagina": "2"}, HX),
            "group sheet": self._queries(url, {**filters, "filter_modal": "rol"}, HX),
        }

    LISTS = (
        ("home", {}),
        ("home", {"weergave": "opdracht"}),
        ("assignment-list", {}),
        ("admin-users", {}),
        ("bezetting", {}),
    )

    def test_no_request_grows_with_the_list(self):
        self._grow(3)
        small = {(name, str(extra), filtered): None for name, extra in self.LISTS for filtered in (False, True)}
        for name, extra in self.LISTS:
            for filtered in (False, True):
                params = {**extra, **(self._filters() if filtered else {})}
                small[(name, str(extra), filtered)] = self._request_kinds(reverse(name), params)
        self._grow(12)
        for name, extra in self.LISTS:
            for filtered in (False, True):
                params = {**extra, **(self._filters() if filtered else {})}
                with self.subTest(list=name, extra=extra, filtered=filtered):
                    assert self._request_kinds(reverse(name), params) == small[(name, str(extra), filtered)]

    def test_next_page_skips_the_filter_counts(self):
        self._grow(3)
        for name, extra in self.LISTS:
            params = {**extra, **self._filters()}
            with self.subTest(list=name, extra=extra):
                kinds = self._request_kinds(reverse(name), params)
                assert kinds["next page"] < kinds["filter change"] < kinds["full"]

    def test_group_sheet_skips_the_rows(self):
        # Unfiltered, so the filter change has rows to load.
        self._grow(3)
        for name, extra in self.LISTS:
            params = dict(extra)
            with self.subTest(list=name, extra=extra):
                kinds = self._request_kinds(reverse(name), params)
                assert kinds["group sheet"] < kinds["filter change"]

    def test_side_panel_skips_the_list(self):
        """Opening a panel costs what the panel costs: the list underneath is not
        rebuilt for it, so its cost does not grow with the list, and it is the
        same on every list (bezetting adds its access check)."""
        self._grow(3)
        lists = ("home", "assignment-list", "bezetting")
        panels = {"collega": str(self.colleague.public_id), "opdracht": str(self.assignment.public_id)}

        def costs():
            return {
                (name, param): self._queries(reverse(name), {**self._filters(), param: value}, PANEL)
                for name in lists
                for param, value in panels.items()
            }

        small = costs()
        for param in panels:
            assert small[("home", param)] == small[("assignment-list", param)] == small[("bezetting", param)] - 1
        self._grow(12)
        assert costs() == small
