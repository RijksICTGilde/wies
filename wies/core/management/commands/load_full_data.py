"""Generate dummy data for the Wies project.

Syncs real organizations from organisaties.overheid.nl, then generates
colleagues, assignments, services, and placements with realistic Dutch names
and government project names.

Usage:
    python manage.py load_full_data               # Full dataset
"""

import logging
import random
import re
from datetime import UTC, date, datetime, timedelta

from django.core.management.base import BaseCommand

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.services.organizations import get_org_descendant_ids, sync_organizations

logger = logging.getLogger(__name__)

# ── Target counts ────────────────────────────────────────────────────────────
NUM_COLLEAGUES = 800
NUM_ASSIGNMENTS = 530
NUM_PLACEMENTS = 800

# ── Distribution settings ────────────────────────────────────────────────────
ACTIVE_RATIO = 0.85
RIJKSOVERHEID_RATIO = 0.90

ASSIGNMENT_STATUS_WEIGHTS = {"INGEVULD": 70, "VACATURE": 20, "LEAD": 10}
SOURCE_WEIGHTS = {"otys_iir": 85, "wies": 15}
SERVICE_SKILL_PROBABILITY = 0.9
SINGLE_PLACEMENT_THRESHOLD = 0.80
DOUBLE_PLACEMENT_THRESHOLD = 0.95

# ── Skills ───────────────────────────────────────────────────────────────────
SKILLS = [
    "Backend development",
    "Frontend development",
    "Product owner",
    "UX designer",
    "AI Consultant",
    "AI Jurist",
    "Researcher",
    "Data engineer",
    "Project leader",
    "(Interim) Manager",
    "Procesbegeleider",
    "Organisatieadviseur",
    "Programmamanager",
    "Beleidsadviseur",
    "Kwartiermaker",
    "Verandermanager",
    "I-Adviseur",
    "CIO",
    "Solution Architect",
    "Cybersecurity Specialist",
    "Data Architect",
    "Privacy Officer",
    "Scrum Master",
    "Business Analist",
    "DevOps Engineer",
    "Test Manager",
    "Information Manager",
    "Process Analyst",
]

# ── Dutch name pools ────────────────────────────────────────────────────────
FIRST_NAMES = [
    # Male
    "Jan",
    "Pieter",
    "Willem",
    "Daan",
    "Sem",
    "Thomas",
    "Lars",
    "Luuk",
    "Jesse",
    "Bram",
    "Max",
    "Ruben",
    "Kevin",
    "Jeroen",
    "Marco",
    "Erik",
    "Bas",
    "Sander",
    "Mark",
    "Joost",
    "Niels",
    "Floris",
    "Stijn",
    "Wouter",
    "Martijn",
    "Rob",
    "Frank",
    "Henk",
    "Kees",
    "Arjan",
    "Dennis",
    "Rick",
    "Stefan",
    "Thijs",
    "Maarten",
    "Vincent",
    "Paul",
    "Michiel",
    "Joris",
    "Tim",
    "Gert",
    "Dirk",
    "Hugo",
    "Oscar",
    "Ties",
    "Hidde",
    "Levi",
    "Mees",
    "Finn",
    "Noud",
    "Siem",
    "Guus",
    "Pim",
    "Tijn",
    "Wout",
    "Jelle",
    # Female
    "Lisa",
    "Emma",
    "Sophie",
    "Anna",
    "Sanne",
    "Femke",
    "Marloes",
    "Inge",
    "Nadia",
    "Yasmin",
    "Sarah",
    "Laura",
    "Julia",
    "Fleur",
    "Iris",
    "Lotte",
    "Roos",
    "Maaike",
    "Ellen",
    "Monique",
    "Esther",
    "Petra",
    "Anouk",
    "Miriam",
    "Anke",
    "Carmen",
    "Denise",
    "Wendy",
    "Nicole",
    "Linda",
    "Diana",
    "Suzanne",
    "Marieke",
    "Annelies",
    "Carolien",
    "Judith",
    "Renate",
    "Bianca",
    "Eva",
    "Tessa",
    "Kim",
    "Joyce",
    "Manon",
    "Naomi",
    "Bo",
    "Noor",
    "Fenna",
    "Mila",
    "Yara",
    "Evi",
    "Olivia",
    "Sara",
    "Hanna",
    "Merel",
    # Multicultural
    "Mohammed",
    "Ahmed",
    "Youssef",
    "Ibrahim",
    "Ali",
    "Hassan",
    "Omar",
    "Fatima",
    "Aisha",
    "Samira",
    "Leila",
    "Amina",
    "Nour",
    "Mariam",
    "Wei",
    "Chen",
    "Priya",
    "Raj",
    "Arjun",
    "Anil",
    "Andrei",
    "Elena",
    "Katarzyna",
    "Tomasz",
    "Ana",
    "Carlos",
]

LAST_NAMES = [
    "de Jong",
    "Jansen",
    "de Vries",
    "van den Berg",
    "van Dijk",
    "Bakker",
    "Janssen",
    "Visser",
    "Smit",
    "Meijer",
    "de Boer",
    "Mulder",
    "de Groot",
    "Bos",
    "Vos",
    "Peters",
    "Hendriks",
    "van Leeuwen",
    "Dekker",
    "Brouwer",
    "de Wit",
    "Dijkstra",
    "Smits",
    "de Graaf",
    "van der Meer",
    "van der Linden",
    "Kok",
    "Jacobs",
    "de Haan",
    "Vermeer",
    "van den Heuvel",
    "van der Veen",
    "van den Broek",
    "de Bruijn",
    "de Leeuw",
    "Kramer",
    "van Wijk",
    "Willems",
    "Hoekstra",
    "Maas",
    "Verhoeven",
    "Koster",
    "van Dam",
    "van der Wal",
    "Prins",
    "Schouten",
    "van Beek",
    "Kuiper",
    "Scholten",
    "van Vliet",
    "Groenewegen",
    "Molenaar",
    "van Rijn",
    "Timmermans",
    "Hermans",
    "Bosman",
    "van der Heijden",
    "Postma",
    "Blom",
    "Gerritsen",
    # Multicultural
    "El Amrani",
    "Yilmaz",
    "Ozdemir",
    "Kaya",
    "Demir",
    "Nguyen",
    "Chen",
    "Patel",
    "Kumar",
    "Singh",
    "El Hadj",
    "Osman",
    "Kowalski",
    "Santos",
    "Popov",
    "Ben Ali",
    "Tahiri",
    "Achahbar",
    "El Idrissi",
    "Bouhali",
]

# ── Assignment name building blocks ─────────────────────────────────────────
PROJECT_ACTIONS = [
    "Herontwerp",
    "Implementatie",
    "Migratie",
    "Optimalisatie",
    "Modernisering",
    "Vernieuwing",
    "Ontwikkeling",
    "Opzet",
    "Proof of Concept",
    "Uitrol",
    "Integratie",
    "Doorontwikkeling",
    "Inrichting",
    "Transitie",
    "Evaluatie",
    "Herziening",
]

PROJECT_DOMAINS = [
    "Identiteitsplatform",
    "Data Platform",
    "Informatiesysteem",
    "Zaaksysteem",
    "Portaal",
    "Dashboard",
    "Registratie",
    "Werkplek",
    "Cloudinfrastructuur",
    "Architectuur",
    "Dienstverleningsportaal",
    "Analysesysteem",
    "Managementinformatie",
    "Ketenintegratie",
    "Basisregistratie",
    "API-platform",
    "Meldingensysteem",
]

PROJECT_TOPICS = [
    "Cybersecurity",
    "AI",
    "Open Data",
    "Privacy",
    "Informatiebeveiliging",
    "Digitale Toegankelijkheid",
    "Algoritmeregister",
    "Wetgevingskalender",
    "Begrotingscyclus",
    "Personeelsplanning",
    "Subsidieregister",
    "Vergunningen",
    "Burgerzaken",
    "Handhaving",
    "Klimaatadaptatie",
    "Energietransitie",
    "Circulaire Economie",
    "Arbeidsmarkt",
    "Zorgdata",
    "Onderwijs",
    "Veiligheid",
    "Migratie",
    "Wonen",
    "Infrastructuur",
    "Landbouw",
    "Inkoop en Aanbesteding",
    "Financieel Beheer",
    "Bedrijfsvoering",
    "Digitale Overheid",
    "Informatiehuishouding",
]

SERVICE_DESCRIPTIONS = [
    "Backend ontwikkeling",
    "Frontend ontwikkeling",
    "Full-stack ontwikkeling",
    "Data engineering",
    "Data analyse",
    "Machine learning",
    "UX/UI ontwerp",
    "Projectleiding",
    "Programmamanagement",
    "Architectuur advies",
    "Security advies",
    "Privacy advies",
    "Agile coaching",
    "Scrum mastering",
    "Product ownership",
    "Beleidsadvies",
    "Procesoptimalisatie",
    "Verandermanagement",
    "Cloud migratie",
    "DevOps implementatie",
    "Test management",
    "Onderzoek en analyse",
    "Kwartiermaking",
    "Interim management",
    "AI consultancy",
    "Informatiemanagement",
    "Ketenbeheer",
]


# ── Helpers ──────────────────────────────────────────────────────────────────


def weighted_choice(rng: random.Random, options: dict[str, int]) -> str:
    return rng.choices(list(options.keys()), weights=list(options.values()))[0]


def generate_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def sanitize_email(name: str) -> str:
    s = name.lower()
    for old, new in [("é", "e"), ("ë", "e"), ("ï", "i"), ("ö", "o"), ("ü", "u")]:
        s = s.replace(old, new)
    s = re.sub(r"[^a-z0-9]", ".", s)
    return re.sub(r"\.+", ".", s).strip(".")


def generate_assignment_name(rng: random.Random) -> str:
    patterns = [
        lambda: f"{rng.choice(PROJECT_ACTIONS)} {rng.choice(PROJECT_DOMAINS)} {rng.choice(PROJECT_TOPICS)}",
        lambda: f"{rng.choice(PROJECT_ACTIONS)} {rng.choice(PROJECT_TOPICS)}",
        lambda: f"{rng.choice(PROJECT_TOPICS)} {rng.choice(PROJECT_DOMAINS)}",
    ]
    return rng.choice(patterns)()


def active_dates(rng: random.Random, ref: date) -> tuple[date, date]:
    start = ref + timedelta(days=rng.randint(-730, 180))
    duration = rng.randint(90, 730)
    end = start + timedelta(days=duration)
    if end <= ref:
        end = ref + timedelta(days=rng.randint(30, 365))
    return start, end


def historic_dates(rng: random.Random, ref: date) -> tuple[date, date]:
    end = ref + timedelta(days=rng.randint(-1095, -30))
    duration = rng.randint(90, 540)
    start = end - timedelta(days=duration)
    return start, end


def classify_orgs_from_db() -> tuple[list[int], list[int]]:
    """Split org PKs into (rijksoverheid_non_root, other) using DB data."""
    ministry_type = OrganizationType.objects.filter(name="Ministerie").first()
    if not ministry_type:
        all_pks = list(OrganizationUnit.objects.values_list("id", flat=True))
        return all_pks, []

    ministry_root_pks = list(ministry_type.organizationunit_set.values_list("id", flat=True))
    rijks_all = get_org_descendant_ids(ministry_root_pks)

    rijks_non_root = [pk for pk in rijks_all if pk not in set(ministry_root_pks)]
    if not rijks_non_root:
        rijks_non_root = list(rijks_all)

    other = list(OrganizationUnit.objects.exclude(id__in=rijks_all).values_list("id", flat=True))

    return rijks_non_root, other


class Command(BaseCommand):
    help = "Generate dummy data: sync organizations, then create colleagues, assignments, services, and placements"

    def handle(self, *args, **options):  # noqa: C901
        rng = random.Random(42)  # noqa: S311
        today = datetime.now(tz=UTC).date()

        # ── 0. Clean up existing dummy data ──────────────────────────────
        self.stdout.write("Cleaning up existing data...")
        Placement.objects.all().delete()
        Service.objects.all().delete()
        Assignment.objects.all().delete()
        Colleague.objects.all().delete()
        OrganizationUnit.objects.update(parent=None)
        OrganizationUnit.objects.all().delete()

        # ── 1. Organizations (via sync service) ──────────────────────────
        self.stdout.write("Syncing organizations from organisaties.overheid.nl...")
        result = sync_organizations()
        self.stdout.write(
            f"  Sync: created={result.created}, updated={result.updated}, "
            f"unchanged={result.unchanged}, deactivated={result.deactivated}"
        )

        org_count = OrganizationUnit.objects.filter(end_date__isnull=True).count()
        self.stdout.write(f"  Active organizations: {org_count}")

        # ── 2. Skills ────────────────────────────────────────────────────
        skills = []
        for name in SKILLS:
            skill, _ = Skill.objects.get_or_create(name=name)
            skills.append(skill)
        self.stdout.write(f"Skills: {len(skills)}")

        # ── 3. Classify orgs for assignment distribution ─────────────────
        rijks_pks, other_pks = classify_orgs_from_db()
        self.stdout.write(f"Rijksoverheid orgs (non-root): {len(rijks_pks)}, Other orgs: {len(other_pks)}")

        # ── 4. Colleagues ────────────────────────────────────────────────
        used_emails: set[str] = set()
        colleagues = []
        for i in range(1, NUM_COLLEAGUES + 1):
            name = generate_name(rng)
            base = sanitize_email(name)
            email = f"{base}@rijksoverheid.nl"
            if email in used_emails:
                email = f"{base}.{i}@rijksoverheid.nl"
            used_emails.add(email)

            num_skills = rng.randint(1, 3)
            chosen_skills = rng.sample(skills, num_skills)

            colleague = Colleague.objects.create(
                name=name,
                email=email,
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            colleague.skills.set(chosen_skills)
            colleagues.append(colleague)
        self.stdout.write(f"Colleagues: {len(colleagues)}")

        # ── 5. Assignments ───────────────────────────────────────────────
        assignments = []
        assignment_statuses: dict[int, str] = {}

        for _ in range(NUM_ASSIGNMENTS):
            status = weighted_choice(rng, ASSIGNMENT_STATUS_WEIGHTS)
            is_active = rng.random() < ACTIVE_RATIO
            start, end = active_dates(rng, today) if is_active else historic_dates(rng, today)

            assignment = Assignment.objects.create(
                name=generate_assignment_name(rng),
                start_date=start,
                end_date=end,
                status=status,
                extra_info="",
                owner=rng.choice(colleagues),
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            assignments.append(assignment)
            assignment_statuses[assignment.id] = status
        self.stdout.write(f"Assignments: {len(assignments)}")

        # ── 6. Assignment ↔ Organization links ───────────────────────────
        for assignment in assignments:
            if rng.random() < RIJKSOVERHEID_RATIO and rijks_pks:
                org_pk = rng.choice(rijks_pks)
            elif other_pks:
                org_pk = rng.choice(other_pks)
            else:
                org_pk = rng.choice(rijks_pks) if rijks_pks else 1
            AssignmentOrganizationUnit.objects.create(
                assignment=assignment,
                organization_id=org_pk,
            )

        # ── 7. Services ──────────────────────────────────────────────────
        assignment_services: dict[int, list[Service]] = {a.id: [] for a in assignments}

        # First pass: each assignment gets at least 1 service
        shuffled_assignments = list(assignments)
        rng.shuffle(shuffled_assignments)

        for assignment in shuffled_assignments:
            skill = rng.choice(skills) if rng.random() < SERVICE_SKILL_PROBABILITY else None
            service = Service.objects.create(
                assignment=assignment,
                description=rng.choice(SERVICE_DESCRIPTIONS),
                skill=skill,
                period_source="ASSIGNMENT",
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            assignment_services[assignment.id].append(service)

        # Second pass: add extra services to INGEVULD assignments for enough placements
        ingevuld_assignments = [a for a in assignments if assignment_statuses[a.id] == "INGEVULD"]
        target_placeable = NUM_PLACEMENTS + 50
        current_placeable = sum(
            len(svcs) for a_id, svcs in assignment_services.items() if assignment_statuses[a_id] == "INGEVULD"
        )
        while current_placeable < target_placeable:
            assignment = rng.choice(ingevuld_assignments)
            skill = rng.choice(skills) if rng.random() < SERVICE_SKILL_PROBABILITY else None
            service = Service.objects.create(
                assignment=assignment,
                description=rng.choice(SERVICE_DESCRIPTIONS),
                skill=skill,
                period_source="ASSIGNMENT",
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            assignment_services[assignment.id].append(service)
            current_placeable += 1

        total_services = Service.objects.count()
        self.stdout.write(f"Services: {total_services}")

        # ── 8. Placements ────────────────────────────────────────────────
        placeable_services = []
        for a_id, svcs in assignment_services.items():
            if assignment_statuses[a_id] == "INGEVULD":
                placeable_services.extend(svcs)
        rng.shuffle(placeable_services)

        # Determine how many placements each colleague gets
        colleague_targets: dict[int, int] = {}
        for colleague in colleagues:
            r = rng.random()
            if r < SINGLE_PLACEMENT_THRESHOLD:
                colleague_targets[colleague.id] = 1
            elif r < DOUBLE_PLACEMENT_THRESHOLD:
                colleague_targets[colleague.id] = 2
            else:
                colleague_targets[colleague.id] = rng.randint(3, 4)

        placement_count = 0
        service_idx = 0

        shuffled_colleagues = list(colleagues)
        rng.shuffle(shuffled_colleagues)

        for colleague in shuffled_colleagues:
            for _ in range(colleague_targets[colleague.id]):
                if service_idx >= len(placeable_services) or placement_count >= NUM_PLACEMENTS:
                    break
                service = placeable_services[service_idx]
                service_idx += 1

                Placement.objects.create(
                    colleague=colleague,
                    service=service,
                    period_source="SERVICE",
                    specific_start_date=None,
                    specific_end_date=None,
                    source=weighted_choice(rng, SOURCE_WEIGHTS),
                    source_id="",
                )
                placement_count += 1

        self.stdout.write(f"Placements: {placement_count}")
        self.stdout.write(self.style.SUCCESS("Done!"))
