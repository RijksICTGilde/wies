from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from wies.core.models import Assignment, Colleague, Label, LabelCategory, Placement, Service
from wies.core.services.colleagues import dedupe_colleagues

User = get_user_model()


class DedupeColleaguesTest(TestCase):
    """Tests for dedupe_colleagues service."""

    def setUp(self):
        # The case-insensitive unique index blocks creating the kind of
        # duplicates this test exercises (production duplicates exist precisely
        # because the previous constraint was case-sensitive). Drop it for the
        # duration of the test — Django wraps each test in a transaction that
        # rolls back this DDL automatically. Django emits expression-based
        # UniqueConstraint as a UNIQUE INDEX rather than a CONSTRAINT.
        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX IF EXISTS unique_colleague_email_source_ci")

    def _run(self):
        return dedupe_colleagues(Colleague, Placement, Assignment)

    def test_no_duplicates_is_noop(self):
        Colleague.objects.create(name="A", email="a@x.nl", source="wies")
        Colleague.objects.create(name="B", email="b@x.nl", source="wies")

        merged = self._run()

        assert merged == 0
        assert Colleague.objects.count() == 2

    def test_skips_groups_with_blank_email(self):
        # Two colleagues with empty email shouldn't be merged together
        Colleague.objects.create(name="A", email="", source="wies")
        Colleague.objects.create(name="B", email="", source="otys_iir", source_id="1")

        merged = self._run()

        assert merged == 0
        assert Colleague.objects.count() == 2

    def test_does_not_merge_across_sources(self):
        # An OTYS colleague and a wies colleague for the same email are legitimate
        # distinct records and must not be merged.
        c_otys = Colleague.objects.create(name="Otys", email="x@x.nl", source="otys_iir", source_id="1")
        c_wies = Colleague.objects.create(name="Wies", email="X@x.nl", source="wies")

        merged = self._run()

        assert merged == 0
        assert Colleague.objects.filter(id=c_otys.id).exists()
        assert Colleague.objects.filter(id=c_wies.id).exists()

    def test_merges_case_insensitive_duplicates(self):
        c1 = Colleague.objects.create(name="C1", email="John@x.nl", source="wies")
        c2 = Colleague.objects.create(name="C2", email="john@x.nl", source="wies")

        merged = self._run()

        assert merged == 1
        # Lowest id wins when no other tiebreaker applies
        assert Colleague.objects.filter(id=c1.id).exists()
        assert not Colleague.objects.filter(id=c2.id).exists()

    def test_canonical_prefers_linked_user(self):
        c_no_user = Colleague.objects.create(name="No User", email="x@x.nl", source="wies")
        user = User.objects.create_user(email="x@x.nl", first_name="X", last_name="Y")
        c_with_user = Colleague.objects.create(name="With User", email="X@x.nl", source="wies", user=user)

        merged = self._run()

        assert merged == 1
        # The one with the linked user wins, even though the other has a lower id
        assert Colleague.objects.filter(id=c_with_user.id).exists()
        assert not Colleague.objects.filter(id=c_no_user.id).exists()

    def test_repoints_placements(self):
        canonical = Colleague.objects.create(name="Canon", email="x@x.nl", source="wies")
        duplicate = Colleague.objects.create(name="Dup", email="X@x.nl", source="wies")

        assignment = Assignment.objects.create(name="A", source="wies")
        service = Service.objects.create(assignment=assignment, description="svc", source="wies")
        placement = Placement.objects.create(colleague=duplicate, service=service, source="wies")

        merged = self._run()

        assert merged == 1
        placement.refresh_from_db()
        assert placement.colleague_id == canonical.id

    def test_repoints_assignment_owner(self):
        canonical = Colleague.objects.create(name="Canon", email="x@x.nl", source="wies")
        duplicate = Colleague.objects.create(name="Dup", email="X@x.nl", source="wies")

        assignment = Assignment.objects.create(name="A", source="wies", owner=duplicate)

        merged = self._run()

        assert merged == 1
        assignment.refresh_from_db()
        assert assignment.owner_id == canonical.id

    def test_unions_labels(self):
        category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#000"})
        label_a = Label.objects.create(name="A", category=category)
        label_b = Label.objects.create(name="B", category=category)

        canonical = Colleague.objects.create(name="Canon", email="x@x.nl", source="wies")
        canonical.labels.add(label_a)
        duplicate = Colleague.objects.create(name="Dup", email="X@x.nl", source="wies")
        duplicate.labels.add(label_b)

        merged = self._run()

        assert merged == 1
        assert set(canonical.labels.values_list("id", flat=True)) == {label_a.id, label_b.id}

    def test_overlapping_labels_are_not_duplicated(self):
        category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#000"})
        label_a = Label.objects.create(name="A", category=category)

        canonical = Colleague.objects.create(name="Canon", email="x@x.nl", source="wies")
        canonical.labels.add(label_a)
        duplicate = Colleague.objects.create(name="Dup", email="X@x.nl", source="wies")
        duplicate.labels.add(label_a)

        merged = self._run()

        assert merged == 1
        assert list(canonical.labels.values_list("id", flat=True)) == [label_a.id]

    def test_three_way_same_source_merge(self):
        # Three wies colleagues with casing variants of the same email
        c1 = Colleague.objects.create(name="One", email="A@x.nl", source="wies")
        c2 = Colleague.objects.create(name="Two", email="a@X.NL", source="wies")
        user = User.objects.create_user(email="a@x.nl", first_name="A", last_name="B")
        c_user = Colleague.objects.create(name="User", email="a@x.nl", source="wies", user=user)

        merged = self._run()

        assert merged == 2
        assert Colleague.objects.filter(email__iexact="a@x.nl").count() == 1
        assert Colleague.objects.filter(id=c_user.id).exists()
        assert not Colleague.objects.filter(id=c1.id).exists()
        assert not Colleague.objects.filter(id=c2.id).exists()

    def test_cross_source_and_same_source_combined(self):
        # An OTYS row exists alongside two wies casing-variants. The OTYS row is
        # left intact; the two wies rows are merged.
        c_otys = Colleague.objects.create(name="Otys", email="x@x.nl", source="otys_iir", source_id="1")
        c_wies1 = Colleague.objects.create(name="Wies1", email="X@x.nl", source="wies")
        c_wies2 = Colleague.objects.create(name="Wies2", email="x@X.nl", source="wies")

        merged = self._run()

        assert merged == 1
        assert Colleague.objects.filter(id=c_otys.id).exists()
        assert Colleague.objects.filter(id=c_wies1.id).exists()
        assert not Colleague.objects.filter(id=c_wies2.id).exists()
