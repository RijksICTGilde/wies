from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Event,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

User = get_user_model()

DUMP_FILE = Path(__file__).resolve().parents[3] / "wies_datadump_20260413_1857.json"


class MigrateOldDataTest(TestCase):
    """Integration test using the real old env JSON dump."""

    def setUp(self):
        """Pre-seed DB with new env state (labels, categories, 1 user, 1 colleague)."""
        # Simulate new env: label categories with new-env colors
        merk = LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        expertise = LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        thema = LabelCategory.objects.create(name="Thema", color="#FFE9B8")

        # New env labels (29 total) - includes some that overlap with old env
        # and some new-env-only labels like "Mindful Rijk", "Innoveren met Impact"
        new_env_merk_labels = [
            "Gateway review",
            "RADIO",
            "Leer en ontwikkel campus",
            "Rijks I-Traineeship",
            "I-Interim Rijk",
            "Intercoach",
            "Delta review",
            "Rijksconsultants",
            "Mindful Rijk",
            "Rijks ICT Gilde",
            "Innoveren met Impact",
        ]
        for name in new_env_merk_labels:
            Label.objects.create(name=name, category=merk)

        new_env_expertise_labels = [
            "Software en data engineering",
            "AI",
            "Agile, project- programma- en portfoliomanagement",
            "Opleiding, training en ontwikkeling",
            "Cloud en platform technologie",
            "Architectuur en technologie",
            "Interimmanagement en advies",
            "Kennis- en innovatiemanagement",
            "ICT",
            "Proces- en ketenmanagement",
            "Security en privacy",
            "Verander- en transformatiemanagement",
            "Strategie, beleid, governance en compliance",
        ]
        for name in new_env_expertise_labels:
            Label.objects.create(name=name, category=expertise)

        new_env_thema_labels = [
            "Artificiële intelligentie",
            "Digitale weerbaarheid",
            "Ambtelijk en digitaal vakmanschap",
            "Innovatieve en lerende overheid",
            "Netwerksamenwerking",
        ]
        for name in new_env_thema_labels:
            Label.objects.create(name=name, category=thema)

        # Existing user and colleague in new env
        self.existing_user = User.objects.create_user(email="matthijs.beekman@rijksoverheid.nl")
        Colleague.objects.create(
            user=self.existing_user,
            name="Matthijs Beekman",
            email="matthijs.beekman@rijksoverheid.nl",
            source="wies",
        )

    def test_migrate_old_data_from_real_dump(self):
        if not DUMP_FILE.exists():
            self.skipTest(f"Dump file not found: {DUMP_FILE}")

        call_command("migrate_old_data", str(DUMP_FILE))

        # --- Users ---
        # 13 from old dump, but matthijs.beekman already exists → 13 total
        assert User.objects.count() == 13
        # Verify a specific user was created
        assert User.objects.filter(email="robbert.bos@rijksoverheid.nl").exists()
        # Existing user still there
        assert User.objects.filter(email="matthijs.beekman@rijksoverheid.nl").exists()

        # --- Label categories ---
        assert LabelCategory.objects.count() == 3
        # Old env had Merk color #C4DBB7, should be updated to that
        merk = LabelCategory.objects.get(name="Merk")
        assert merk.color == "#C4DBB7"

        # --- Labels ---
        # Old has 28 labels, new has 29 labels. Most overlap by name.
        # New-env-only: "Mindful Rijk", "Innoveren met Impact" (not in old dump)
        # Old-env-only: "ODI Innovatie" (not in new dump)
        # So total should be 29 (new) + 1 (ODI Innovatie) = 30
        assert Label.objects.count() == 30
        assert Label.objects.filter(name="Mindful Rijk").exists()
        assert Label.objects.filter(name="Innoveren met Impact").exists()
        assert Label.objects.filter(name="ODI Innovatie").exists()

        # --- Skills ---
        assert Skill.objects.count() == 15

        # --- Colleagues ---
        assert Colleague.objects.count() == 42
        # Matthijs was merged, not duplicated
        assert Colleague.objects.filter(email="matthijs.beekman@rijksoverheid.nl").count() == 1
        matthijs = Colleague.objects.get(email="matthijs.beekman@rijksoverheid.nl")
        assert matthijs.user is not None
        assert matthijs.user.email == "matthijs.beekman@rijksoverheid.nl"
        # Colleagues with labels should have them remapped
        robbert_bos = Colleague.objects.get(email="robbert.bos@rijksoverheid.nl")
        assert robbert_bos.labels.filter(name="Rijks ICT Gilde").exists()
        assert robbert_bos.user is not None

        # --- Organization types & units ---
        assert OrganizationType.objects.count() == 25
        assert OrganizationUnit.objects.count() == 3850
        # Verify parent hierarchy: some org units should have parents
        units_with_parents = OrganizationUnit.objects.filter(parent__isnull=False).count()
        assert units_with_parents > 0

        # --- Assignments ---
        assert Assignment.objects.count() == 6
        wies_assignment = Assignment.objects.get(name="Wies")
        assert wies_assignment.owner is not None
        # Owner pk=1 in old dump = Robbert Bos
        assert wies_assignment.owner.name == "Robbert Bos"

        # --- AssignmentOrganizationUnit ---
        assert AssignmentOrganizationUnit.objects.count() == 7
        # All should have valid FKs
        for aou in AssignmentOrganizationUnit.objects.all():
            assert aou.assignment_id is not None
            assert aou.organization_id is not None
            assert Assignment.objects.filter(pk=aou.assignment_id).exists()
            assert OrganizationUnit.objects.filter(pk=aou.organization_id).exists()

        # --- Services ---
        assert Service.objects.count() == 23
        for service in Service.objects.all():
            assert Assignment.objects.filter(pk=service.assignment_id).exists()

        # --- Placements ---
        assert Placement.objects.count() == 31
        for placement in Placement.objects.all():
            assert Colleague.objects.filter(pk=placement.colleague_id).exists()
            assert Service.objects.filter(pk=placement.service_id).exists()

        # --- Events should NOT be imported ---
        assert Event.objects.count() == 0
