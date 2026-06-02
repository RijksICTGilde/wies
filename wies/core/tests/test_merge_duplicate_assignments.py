from django.contrib.auth import get_user_model
from django.test import TestCase

from wies.core.management.commands.merge_duplicate_assignments import (
    find_duplicate_groups,
    merge_group,
)
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

User = get_user_model()


class MergeDuplicateAssignmentsTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(email="owner@x.nl", first_name="Owner", last_name="BDM")
        self.owner = Colleague.objects.create(user=user, name="Owner BDM", email="owner@x.nl", source="wies")
        self.org = OrganizationUnit.objects.create(name="Org A", abbreviations=["OA"])
        self.org_b = OrganizationUnit.objects.create(name="Org B", abbreviations=["OB"])
        self.skill = Skill.objects.create(name="Developer")
        self._user_counter = 0

    def _make_assignment(self, name, org=None, **kwargs):
        a = Assignment.objects.create(name=name, owner=self.owner, source="wies", **kwargs)
        if org:
            AssignmentOrganizationUnit.objects.create(assignment=a, organization=org, role="PRIMARY")
        return a

    def _make_service(self, assignment, colleague_name=None):
        svc = Service.objects.create(assignment=assignment, skill=self.skill, description="desc", source="wies")
        if colleague_name:
            self._user_counter += 1
            u = User.objects.create_user(
                email=f"user{self._user_counter}@x.nl",
                first_name=colleague_name.split()[0],
                last_name=colleague_name.split()[-1] if " " in colleague_name else "X",
            )
            col = Colleague.objects.create(
                user=u,
                name=colleague_name,
                email=f"user{self._user_counter}@x.nl",
                source="wies",
            )
            Placement.objects.create(colleague=col, service=svc, source="wies")
        return svc

    def test_find_duplicate_groups(self):
        self._make_assignment("CIV", self.org)
        self._make_assignment("CIV", self.org)
        self._make_assignment("Unique", self.org)

        groups = find_duplicate_groups()
        assert len(groups) == 1
        assert len(groups[0]) == 2
        assert all(a.name == "CIV" for a in groups[0])

    def test_no_duplicates(self):
        self._make_assignment("A", self.org)
        self._make_assignment("B", self.org)

        groups = find_duplicate_groups()
        assert len(groups) == 0

    def test_different_owners_not_grouped(self):
        user2 = User.objects.create_user(email="other@x.nl", first_name="Other", last_name="BDM")
        owner2 = Colleague.objects.create(user=user2, name="Other BDM", email="other@x.nl", source="wies")

        self._make_assignment("CIV", self.org)
        Assignment.objects.create(name="CIV", owner=owner2, source="wies")

        groups = find_duplicate_groups()
        assert len(groups) == 0

    def test_merge_moves_services(self):
        a1 = self._make_assignment("CIV", self.org, start_date="2026-01-01", end_date="2026-06-01")
        a2 = self._make_assignment("CIV", self.org, start_date="2026-03-01", end_date="2026-09-01")

        svc1 = self._make_service(a1, "Alice")
        svc2 = self._make_service(a2, "Bob")

        merge_group([a1, a2], dry_run=False)

        # Services moved to target.
        svc1.refresh_from_db()
        svc2.refresh_from_db()
        assert svc1.assignment_id == a1.id
        assert svc2.assignment_id == a1.id

        # Placements still intact.
        assert svc1.placements.count() == 1
        assert svc2.placements.count() == 1
        assert svc1.placements.first().colleague.name == "Alice"
        assert svc2.placements.first().colleague.name == "Bob"

        # Duplicate deleted.
        assert not Assignment.objects.filter(id=a2.id).exists()

        # Period widened.
        a1.refresh_from_db()
        assert str(a1.start_date) == "2026-01-01"
        assert str(a1.end_date) == "2026-09-01"

    def test_merge_consolidates_orgs(self):
        a1 = self._make_assignment("CIV", self.org)
        a2 = self._make_assignment("CIV", None)
        AssignmentOrganizationUnit.objects.create(assignment=a2, organization=self.org_b, role="PRIMARY")

        merge_group([a1, a2], dry_run=False)

        # Target has original PRIMARY + duplicate's PRIMARY demoted to INVOLVED.
        rels = AssignmentOrganizationUnit.objects.filter(assignment=a1)
        assert rels.count() == 2
        assert rels.filter(organization=self.org, role="PRIMARY").exists()
        assert rels.filter(organization=self.org_b, role="INVOLVED").exists()

    def test_merge_deduplicates_orgs(self):
        a1 = self._make_assignment("CIV", self.org)
        a2 = self._make_assignment("CIV", None)
        # Same org as PRIMARY on the duplicate.
        AssignmentOrganizationUnit.objects.create(assignment=a2, organization=self.org, role="PRIMARY")

        merge_group([a1, a2], dry_run=False)

        # No duplicate org relations.
        rels = AssignmentOrganizationUnit.objects.filter(assignment=a1)
        assert rels.count() == 1
        assert rels.filter(organization=self.org, role="PRIMARY").exists()

    def test_dry_run_does_not_change_data(self):
        a1 = self._make_assignment("CIV", self.org)
        a2 = self._make_assignment("CIV", self.org)
        self._make_service(a2, "Bob")

        merge_group([a1, a2], dry_run=True)

        # Both assignments still exist.
        assert Assignment.objects.filter(id=a1.id).exists()
        assert Assignment.objects.filter(id=a2.id).exists()
        # Service still on duplicate.
        assert a2.services.count() == 1

    def test_merge_three_assignments(self):
        a1 = self._make_assignment("CIV", self.org, start_date="2026-01-01", end_date="2026-06-01")
        a2 = self._make_assignment("CIV", None, start_date="2026-02-01", end_date="2026-07-01")
        a3 = self._make_assignment("CIV", None, start_date="2026-03-01", end_date="2026-08-01")

        self._make_service(a1, "Alice")
        self._make_service(a2, "Bob")
        self._make_service(a3, "Charlie")

        merge_group([a1, a2, a3], dry_run=False)

        a1.refresh_from_db()
        assert a1.services.count() == 3
        assert not Assignment.objects.filter(id=a2.id).exists()
        assert not Assignment.objects.filter(id=a3.id).exists()
        assert str(a1.start_date) == "2026-01-01"
        assert str(a1.end_date) == "2026-08-01"

    def test_merge_extra_info(self):
        a1 = self._make_assignment("CIV", self.org)
        a1.extra_info = "Info from A"
        a1.save()
        a2 = self._make_assignment("CIV", None)
        a2.extra_info = "Info from B"
        a2.save()

        merge_group([a1, a2], dry_run=False)

        a1.refresh_from_db()
        assert "Info from A" in a1.extra_info
        assert "Info from B" in a1.extra_info
