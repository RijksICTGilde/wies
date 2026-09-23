"""Tests for the interim OTYS Excel import.

Workbooks are built in-memory from a small helper so the tests never depend on a
checked-in data file, and so the layout-drift test can reshuffle columns freely.
"""

import datetime
import io

import openpyxl
import pytest
from django.test import TestCase

from wies.core.management.commands.load_full_data import BASE_MINISTRIES, seed_base_organizations
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Suborganization,
)
from wies.core.services.otys_import import ExcelParseError, import_batch, parse_excel
from wies.core.services.otys_import.ministries import MINISTRY_SYSTEM_IDS

# --- workbook builders -----------------------------------------------------

VACANCY_HEADERS = [
    "Referentie", "Functietitel", "Consultant", "Consultant Email",
    "Startdatum", "Einddatum", "Functie omschrijving", "02. Ministerie(s)",
    "03. Functies",
]
VACANCY_ROW = [
    "RIG03965", "Programma CIO ERTMS I&W", "Coen van Loon",
    "Coen.Loon@rijksoverheid.nl", datetime.datetime(2026, 1, 1),
    datetime.datetime(2027, 12, 31), "Toetst de ICT-realisatie.", "I&W",
    "CIO",
]

PLACEMENT_HEADERS = [
    "Plaatsing - Plaatsingsnummer", "Plaatsing - Vacature referentienummer",
    "Kandidaat - Achternaam", "Kandidaat - Voornaam", "Kandidaat – Email",
    "Plaatsing - Startdatum", "Plaatsing - Einddatum",
]
PLACEMENT_ROW = [
    "ARIPK2370", "RIG03965", "Kolkman", "Pascal",
    "Pascal.Kolkman@rijksoverheid.nl", datetime.datetime(2026, 1, 1),
    datetime.datetime(2027, 12, 31),
]


def build_workbook(vacancy_headers=None, vacancy_row=None, placement_headers=None,
                   placement_row=None, lead_blank_rows=0):
    """Builds an OTYS-shaped workbook. Parameters let a test reorder or shift."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IIR-Detachering1"
    for _ in range(lead_blank_rows):
        ws.append([])
    ws.append(["Uitleg-regel bovenaan"])
    ws.append([])
    ws.append(["Vacature module"])
    ws.append(vacancy_headers or VACANCY_HEADERS)
    ws.append(vacancy_row or VACANCY_ROW)
    ws.append([])
    ws.append(["Plaatsingenmodule"])
    ws.append(placement_headers or PLACEMENT_HEADERS)
    ws.append(placement_row or PLACEMENT_ROW)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# --- parser tests ----------------------------------------------------------


class ParseExcelTest(TestCase):
    def test_parses_vacancy_and_linked_placement(self):
        batch = parse_excel(build_workbook())

        assert len(batch.vacancies) == 1
        vacancy = batch.vacancies[0]
        assert vacancy.reference == "RIG03965"
        assert vacancy.name == "Programma CIO ERTMS I&W"
        assert vacancy.owner_email == "Coen.Loon@rijksoverheid.nl"
        assert vacancy.ministry_code == "I&W"
        assert vacancy.role == "CIO"
        assert vacancy.start_date == datetime.date(2026, 1, 1)
        assert vacancy.end_date == datetime.date(2027, 12, 31)

        assert len(batch.placements) == 1
        placement = batch.placements[0]
        assert placement.placement_number == "ARIPK2370"
        assert placement.vacancy_reference == "RIG03965"
        assert placement.candidate.email == "Pascal.Kolkman@rijksoverheid.nl"
        assert placement.candidate.name == "Pascal Kolkman"
        # The placement links back to its vacancy via the reference.
        assert batch.vacancy_by_reference(placement.vacancy_reference) is vacancy

    def test_layout_drift_reordered_columns_and_shifted_rows(self):
        """Columns reordered and tables shifted down still parse identically."""
        reordered_vacancy_headers = [
            "02. Ministerie(s)", "Consultant Email", "Referentie", "Einddatum",
            "Consultant", "Startdatum", "Functietitel", "Functie omschrijving",
        ]
        reordered_vacancy_row = [
            "I&W", "Coen.Loon@rijksoverheid.nl", "RIG03965",
            datetime.datetime(2027, 12, 31), "Coen van Loon",
            datetime.datetime(2026, 1, 1), "Programma CIO ERTMS I&W", "Toetst.",
        ]
        reordered_placement_headers = [
            "Kandidaat – Email", "Plaatsing - Vacature referentienummer",
            "Kandidaat - Voornaam", "Plaatsing - Plaatsingsnummer",
            "Kandidaat - Achternaam",
        ]
        reordered_placement_row = [
            "Pascal.Kolkman@rijksoverheid.nl", "RIG03965", "Pascal", "ARIPK2370", "Kolkman",
        ]
        data = build_workbook(
            vacancy_headers=reordered_vacancy_headers,
            vacancy_row=reordered_vacancy_row,
            placement_headers=reordered_placement_headers,
            placement_row=reordered_placement_row,
            lead_blank_rows=4,
        )
        batch = parse_excel(data)

        assert batch.vacancies[0].reference == "RIG03965"
        assert batch.vacancies[0].name == "Programma CIO ERTMS I&W"
        assert batch.vacancies[0].start_date == datetime.date(2026, 1, 1)
        assert batch.placements[0].placement_number == "ARIPK2370"
        assert batch.placements[0].candidate.email == "Pascal.Kolkman@rijksoverheid.nl"

    def test_description_prefers_bedrijfscultuur_over_functie_omschrijving(self):
        """OTYS puts the opdrachtomschrijving in 'Bedrijfscultuur'; that wins,
        with 'Functie omschrijving' only used as a fallback when it's empty."""
        headers = [*VACANCY_HEADERS, "Bedrijfscultuur"]
        # 'Functie omschrijving' is already in VACANCY_ROW; add a Bedrijfscultuur value.
        row = [*VACANCY_ROW, "Programmacontext en cultuur."]
        batch = parse_excel(build_workbook(vacancy_headers=headers, vacancy_row=row))
        assert batch.vacancies[0].description == "Programmacontext en cultuur."

        # When Bedrijfscultuur is empty, fall back to Functie omschrijving.
        row_empty_culture = [*VACANCY_ROW, ""]
        batch2 = parse_excel(build_workbook(vacancy_headers=headers, vacancy_row=row_empty_culture))
        assert batch2.vacancies[0].description == "Toetst de ICT-realisatie."

    def test_missing_required_column_raises(self):
        headers_without_email = [h for h in VACANCY_HEADERS if h != "Consultant Email"]
        row_without_email = [
            v for h, v in zip(VACANCY_HEADERS, VACANCY_ROW, strict=True) if h != "Consultant Email"
        ]
        data = build_workbook(vacancy_headers=headers_without_email, vacancy_row=row_without_email)

        with pytest.raises(ExcelParseError) as exc_info:
            parse_excel(data)
        assert "owner_email" in str(exc_info.value)

    def test_not_an_otys_workbook_raises(self):
        wb = openpyxl.Workbook()
        wb.active.append(["some", "unrelated", "sheet"])
        buffer = io.BytesIO()
        wb.save(buffer)

        with pytest.raises(ExcelParseError):
            parse_excel(buffer.getvalue())


# --- base-profile seeding ---------------------------------------------------


class BaseSeedMinistryLinkTest(TestCase):
    """The offline base profile (``just setup``) must seed every ministry the
    OTYS import can name, so the opdrachtgever link resolves without a network sync."""

    def test_seeded_ministries_resolve_for_import(self):
        Suborganization.objects.create(name="I-Interim Rijk")
        seed_base_organizations()

        # Every system id the import maps to must be seeded and findable the same
        # way the importer looks it up.
        for system_id in set(MINISTRY_SYSTEM_IDS.values()):
            assert OrganizationUnit.objects.filter(source_url__contains=f"/{system_id}/").exists(), system_id

        # And an end-to-end import against the seeded I&W org links the opdrachtgever.
        result = import_batch(parse_excel(build_workbook()), creator=None)
        assert result["success"], result["errors"]
        assert result["organizations_linked"] == 1
        assignment = Assignment.objects.get(source="otys_iir", source_id="RIG03965")
        link = AssignmentOrganizationUnit.objects.get(assignment=assignment)
        assert "/112773/" in link.organization.source_url

        # BASE_MINISTRIES stays aligned with the map (no silent drift).
        seeded_ids = {system_id for _, _, system_id in BASE_MINISTRIES}
        assert set(MINISTRY_SYSTEM_IDS.values()) <= seeded_ids


# --- importer tests --------------------------------------------------------


class ImportBatchTest(TestCase):
    def setUp(self):
        # OTYS colleagues all belong to this seeded brand.
        Suborganization.objects.create(name="I-Interim Rijk")
        # Seed the I&W ministry org with a source_url carrying its system id, so
        # the ministry link resolves.
        ministry_type = OrganizationType.objects.create(name="ministerie", label="Ministerie")
        self.ministry = OrganizationUnit.objects.create(
            name="Infrastructuur en Waterstaat",
            source_url="https://organisaties.overheid.nl/112773/Infrastructuur_en_Waterstaat/",
        )
        self.ministry.organization_types.add(ministry_type)

    def _import(self):
        batch = parse_excel(build_workbook())
        return import_batch(batch, creator=None)

    def test_creates_all_records(self):
        result = self._import()

        assert result["success"], result["errors"]
        assert result["assignments_created"] == 1
        assert result["services_created"] == 1
        assert result["placements_created"] == 1
        assert result["skills_created"] == 1
        # Owner + candidate.
        assert result["colleagues_created"] == 2
        assert result["organizations_linked"] == 1

        assignment = Assignment.objects.get(source="otys_iir", source_id="RIG03965")
        assert assignment.name == "Programma CIO ERTMS I&W"
        assert assignment.owner.email == "Coen.Loon@rijksoverheid.nl"
        assert assignment.start_date == datetime.date(2026, 1, 1)

        service = Service.objects.get(source="otys_iir", source_id="RIG03965")
        assert service.assignment == assignment
        # The vacancy's function (03. Functies) lands as the service's Skill.
        assert service.skill is not None
        assert service.skill.name == "CIO"

        placement = Placement.objects.get(source="otys_iir", source_id="ARIPK2370")
        assert placement.service == service
        assert placement.colleague.email == "Pascal.Kolkman@rijksoverheid.nl"

        link = AssignmentOrganizationUnit.objects.get(assignment=assignment)
        assert link.organization == self.ministry
        assert link.role == "PRIMARY"

    def test_reimport_is_idempotent(self):
        self._import()
        result = self._import()

        assert result["success"], result["errors"]
        # Nothing new on the second run; everything updated in place.
        assert result["assignments_created"] == 0
        assert result["assignments_updated"] == 1
        assert result["placements_created"] == 0
        assert result["placements_updated"] == 1
        assert Assignment.objects.filter(source="otys_iir").count() == 1
        assert Placement.objects.filter(source="otys_iir").count() == 1
        assert Colleague.objects.filter(source="otys_iir").count() == 2

    def test_placement_period_inherits_when_equal_to_assignment(self):
        self._import()
        placement = Placement.objects.get(source="otys_iir", source_id="ARIPK2370")
        # Dates match the vacancy, so the placement inherits (SERVICE).
        assert placement.period_source == "SERVICE"
        assert placement.specific_start_date is None
        assert placement.start_date == datetime.date(2026, 1, 1)
        assert placement.end_date == datetime.date(2027, 12, 31)

    def test_placement_keeps_own_period_when_it_differs(self):
        placement_row = list(PLACEMENT_ROW)
        placement_row[PLACEMENT_HEADERS.index("Plaatsing - Startdatum")] = datetime.datetime(2026, 6, 1)
        placement_row[PLACEMENT_HEADERS.index("Plaatsing - Einddatum")] = datetime.datetime(2027, 6, 30)
        result = import_batch(parse_excel(build_workbook(placement_row=placement_row)), creator=None)

        assert result["success"], result["errors"]
        placement = Placement.objects.get(source="otys_iir", source_id="ARIPK2370")
        # Dates differ from the vacancy, so the placement carries its own period.
        assert placement.period_source == "PLACEMENT"
        assert placement.start_date == datetime.date(2026, 6, 1)
        assert placement.end_date == datetime.date(2027, 6, 30)

    def test_placement_period_switches_back_to_inherit_on_reimport(self):
        # First import with a differing period, then re-import with matching dates.
        differing = list(PLACEMENT_ROW)
        differing[PLACEMENT_HEADERS.index("Plaatsing - Startdatum")] = datetime.datetime(2026, 6, 1)
        import_batch(parse_excel(build_workbook(placement_row=differing)), creator=None)

        self._import()  # matching dates
        placement = Placement.objects.get(source="otys_iir", source_id="ARIPK2370")
        assert placement.period_source == "SERVICE"
        assert placement.specific_start_date is None
        assert placement.specific_end_date is None

    def test_unknown_ministry_fails_whole_import(self):
        row = list(VACANCY_ROW)
        row[VACANCY_HEADERS.index("02. Ministerie(s)")] = "XYZ"
        batch = parse_excel(build_workbook(vacancy_row=row))

        result = import_batch(batch, creator=None)

        assert not result["success"]
        assert any("XYZ" in error for error in result["errors"])
        # Nothing saved: the whole transaction rolled back.
        assert Assignment.objects.filter(source="otys_iir").count() == 0
        assert Colleague.objects.filter(source="otys_iir").count() == 0

    def test_missing_ministry_org_fails_whole_import(self):
        self.ministry.delete()
        result = self._import()

        assert not result["success"]
        assert any("112773" in error for error in result["errors"])
        assert Assignment.objects.filter(source="otys_iir").count() == 0

    def test_placement_referencing_unknown_vacancy_fails(self):
        placement_row = list(PLACEMENT_ROW)
        placement_row[PLACEMENT_HEADERS.index("Plaatsing - Vacature referentienummer")] = "RIG99999"
        batch = parse_excel(build_workbook(placement_row=placement_row))

        result = import_batch(batch, creator=None)

        assert not result["success"]
        assert any("RIG99999" in error for error in result["errors"])
        assert Placement.objects.filter(source="otys_iir").count() == 0
        # The vacancy's own records rolled back too.
        assert Assignment.objects.filter(source="otys_iir").count() == 0

    def test_candidate_without_email_fails(self):
        placement_row = list(PLACEMENT_ROW)
        placement_row[PLACEMENT_HEADERS.index("Kandidaat – Email")] = ""
        batch = parse_excel(build_workbook(placement_row=placement_row))

        result = import_batch(batch, creator=None)

        assert not result["success"]
        assert any("ARIPK2370" in error for error in result["errors"])
        assert Assignment.objects.filter(source="otys_iir").count() == 0

    def test_candidate_name_strips_otys_suffixes(self):
        """OTYS decorates the achternaam; the imported name must be clean."""
        placement_row = list(PLACEMENT_ROW)
        placement_row[PLACEMENT_HEADERS.index("Kandidaat - Achternaam")] = "Kolkman (36) (LenB)"
        batch = parse_excel(build_workbook(placement_row=placement_row))

        assert batch.placements[0].candidate.name == "Pascal Kolkman"

        result = import_batch(batch, creator=None)
        assert result["success"], result["errors"]
        placement = Placement.objects.get(source="otys_iir", source_id="ARIPK2370")
        assert placement.colleague.name == "Pascal Kolkman"
