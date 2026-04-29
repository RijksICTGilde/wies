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
    LabelCategory,
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

SOURCE_WEIGHTS = {"otys_iir": 50, "wies": 50}
SINGLE_PLACEMENT_THRESHOLD = 0.80
DOUBLE_PLACEMENT_THRESHOLD = 0.95
MULTI_LABEL_PROBABILITY = 0.3
MAX_LABELS_PER_CATEGORY = 2

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

SERVICE_DESCRIPTIONS: dict[str, list[str]] = {
    "Backend development": [
        "Ontwikkeling en onderhoud van backend-services en API's voor het centrale platform",
        "Migratie van legacy-systemen naar een moderne microservices-architectuur",
        "Bouwen van koppelingen met externe registraties en basisregistraties",
    ],
    "Frontend development": [
        "Doorontwikkeling van de gebruikersinterface op basis van het NL Design System",
        "Bouwen van toegankelijke formulieren en dashboards conform WCAG-richtlijnen",
        "Implementatie van een componentenbibliotheek voor hergebruik binnen de organisatie",
    ],
    "Product owner": [
        "Beheer van de productbacklog en afstemming met stakeholders over prioriteiten",
        "Vertalen van beleidsdoelen naar concrete user stories en acceptatiecriteria",
        "Begeleiden van de productroadmap en kwartaalplanning voor het digitale platform",
    ],
    "UX designer": [
        "Gebruikersonderzoek en ontwerp van intuïtieve workflows voor interne medewerkers",
        "Herontwerp van de aanvraagprocessen op basis van gebruikerstesten en feedback",
        "Opstellen van interactiepatronen en designrichtlijnen voor het platform",
    ],
    "AI Consultant": [
        "Advies over verantwoorde inzet van AI binnen overheidsprocessen conform de AI-verordening",
        "Verkenning van mogelijkheden voor tekstanalyse en classificatie van documenten",
        "Begeleiding bij de ontwikkeling van een AI-strategie en implementatieroadmap",
    ],
    "AI Jurist": [
        "Juridische toetsing van algoritmes en geautomatiseerde besluitvorming aan de AVG en AI Act",
        "Opstellen van kaders voor transparantie en uitlegbaarheid van AI-systemen",
        "Advies over de juridische aspecten van data-uitwisseling tussen overheidsorganisaties",
    ],
    "Researcher": [
        "Onderzoek naar de effectiviteit van digitale dienstverlening en gebruikerstevredenheid",
        "Uitvoeren van beleidsanalyses en haalbaarheidsstudies voor nieuwe digitale initiatieven",
        "Evaluatie van bestaande systemen en advies over verbetermogelijkheden",
    ],
    "Data engineer": [
        "Inrichten en beheer van datapipelines voor het centrale dataplatform",
        "Ontwikkeling van ETL-processen voor de ontsluiting van bronregistraties",
        "Bouwen van een datawarehouse voor managementrapportages en stuurinformatie",
    ],
    "Project leader": [
        "Leiding geven aan een multidisciplinair team voor de implementatie van een nieuw zaaksysteem",
        "Coördinatie van de planning, risico's en afhankelijkheden binnen het programma",
        "Aansturen van het migratietraject van on-premise naar cloudomgeving",
    ],
    "(Interim) Manager": [
        "Tijdelijke aansturing van het ICT-team tijdens een reorganisatie",
        "Waarneming van het afdelingshoofd en bewaken van de operationele continuïteit",
        "Opbouwen van een nieuw team en inrichten van de werkprocessen",
    ],
    "Procesbegeleider": [
        "Begeleiden van workshops en werksessies voor de herinrichting van werkprocessen",
        "Faciliteren van samenwerking tussen beleid, uitvoering en ICT",
        "Ondersteuning bij het opstellen van procesmodellen en verbeterplannen",
    ],
    "Organisatieadviseur": [
        "Advies over de inrichting van de IT-governance en besluitvormingsstructuur",
        "Analyse van de organisatiecultuur en aanbevelingen voor verandermanagement",
        "Ondersteuning bij de herinrichting van rollen en verantwoordelijkheden",
    ],
    "Programmamanager": [
        "Aansturing van een programma met meerdere projecten rond digitale transformatie",
        "Bewaken van de samenhang tussen projecten en realisatie van programmadoelen",
        "Rapportage aan de stuurgroep en management over voortgang en risico's",
    ],
    "Beleidsadviseur": [
        "Opstellen van beleidskaders voor digitalisering en informatievoorziening",
        "Advisering over de implementatie van nieuwe wet- en regelgeving in digitale systemen",
        "Analyse van beleidsopties en impactbeoordeling voor ICT-investeringen",
    ],
    "Kwartiermaker": [
        "Opzetten van een nieuw team en inrichten van werkprocessen en tooling",
        "Verkenning en voorbereiding van een nieuw programma rond datagedreven werken",
        "Inrichten van de samenwerking met ketenpartners en externe leveranciers",
    ],
    "Verandermanager": [
        "Begeleiden van de organisatie bij de transitie naar agile werken",
        "Ontwikkelen en uitvoeren van een veranderstrategie voor digitale transformatie",
        "Ondersteuning bij de adoptie van nieuwe systemen en werkwijzen door eindgebruikers",
    ],
    "I-Adviseur": [
        "Advies over de informatievoorziening en de samenhang met de enterprise-architectuur",
        "Opstellen van informatiebeleidsplannen en architectuurprincipes",
        "Begeleiding bij de selectie en implementatie van nieuwe informatiesystemen",
    ],
    "CIO": [
        "Strategische aansturing van de IT-organisatie en digitale agenda",
        "Advisering van het bestuur over IT-investeringen en digitale innovatie",
        "Bewaken van de samenhang tussen IT-strategie en organisatiedoelen",
    ],
    "Solution Architect": [
        "Ontwerp van de technische architectuur voor een nieuw registratiesysteem",
        "Bewaken van architectuurprincipes en technische samenhang tussen systemen",
        "Advies over de integratie van cloudoplossingen binnen de bestaande infrastructuur",
    ],
    "Cybersecurity Specialist": [
        "Uitvoeren van risicoanalyses en penetratietesten op kritieke systemen",
        "Inrichten van security monitoring en incident response processen",
        "Advisering over de implementatie van BIO-maatregelen en beveiligingsstandaarden",
    ],
    "Data Architect": [
        "Ontwerp van het datalandschap en de gegevensarchitectuur voor de organisatie",
        "Opstellen van datamodellen en richtlijnen voor gegevensuitwisseling",
        "Advies over de inrichting van master data management en datakwaliteit",
    ],
    "Privacy Officer": [
        "Uitvoeren van DPIA's en toezicht houden op de naleving van de AVG",
        "Opstellen van privacybeleid en verwerkingsregisters voor nieuwe systemen",
        "Advisering over privacy by design bij de ontwikkeling van digitale diensten",
    ],
    "Scrum Master": [
        "Begeleiden van het scrumteam en bewaken van het agile proces",
        "Faciliteren van sprint ceremonies en het wegnemen van impediments",
        "Coaching van teamleden en stakeholders in agile werkwijzen",
    ],
    "Business Analist": [
        "Analyse van bedrijfsprocessen en vertaling naar functionele specificaties",
        "Opstellen van requirements en procesmodellen voor systeemontwikkeling",
        "Begeleiding bij acceptatietesten en validatie van opgeleverde functionaliteit",
    ],
    "DevOps Engineer": [
        "Inrichten en beheer van CI/CD-pipelines en geautomatiseerde deployments",
        "Beheer van de containerplatform-infrastructuur en monitoring",
        "Automatisering van infrastructuur met Infrastructure as Code",
    ],
    "Test Manager": [
        "Opzetten van een teststrategie en coördinatie van testactiviteiten",
        "Inrichten van testautomatisering en kwaliteitsrapportages",
        "Bewaken van de testkwaliteit en advies over testdekking bij releases",
    ],
    "Information Manager": [
        "Afstemming tussen business en IT over informatiebehoeften en prioriteiten",
        "Beheer van het applicatielandschap en advisering over rationalisatie",
        "Opstellen van informatieplannen en bewaken van de informatiearchitectuur",
    ],
    "Process Analyst": [
        "In kaart brengen en analyseren van werkprocessen voor optimalisatie",
        "Modelleren van processen in BPMN en identificeren van verbeterkansen",
        "Ondersteuning bij de implementatie van procesverbeteringen en monitoring",
    ],
}


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

        # ── 4b. Colleague labels ─────────────────────────────────────────
        labels_by_category = {category: list(category.labels.all()) for category in LabelCategory.objects.all()}
        labels_by_category = {k: v for k, v in labels_by_category.items() if v}

        if labels_by_category:
            for colleague in colleagues:
                colleague_labels = []
                for labels in labels_by_category.values():
                    has_enough = len(labels) >= MAX_LABELS_PER_CATEGORY
                    n = MAX_LABELS_PER_CATEGORY if has_enough and rng.random() < MULTI_LABEL_PROBABILITY else 1
                    colleague_labels.extend(rng.sample(labels, n))
                colleague.labels.set(colleague_labels)
            self.stdout.write("Colleague labels assigned")

        # ── 5. Assignments ───────────────────────────────────────────────
        assignments = []

        for _ in range(NUM_ASSIGNMENTS):
            is_active = rng.random() < ACTIVE_RATIO
            start, end = active_dates(rng, today) if is_active else historic_dates(rng, today)

            assignment = Assignment.objects.create(
                name=generate_assignment_name(rng),
                start_date=start,
                end_date=end,
                extra_info="",
                owner=rng.choice(colleagues),
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            assignments.append(assignment)
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
                role="PRIMARY",
            )

        # ── 7. Services ──────────────────────────────────────────────────
        all_services: list[Service] = []

        # First pass: each assignment gets at least 1 service
        shuffled_assignments = list(assignments)
        rng.shuffle(shuffled_assignments)

        for assignment in shuffled_assignments:
            skill = rng.choice(skills)
            service = Service.objects.create(
                assignment=assignment,
                description=rng.choice(SERVICE_DESCRIPTIONS.get(skill.name, [""])),
                skill=skill,
                period_source="ASSIGNMENT",
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            all_services.append(service)

        # Second pass: add extra services until we have enough for placements
        target_placeable = NUM_PLACEMENTS + 50
        while len(all_services) < target_placeable:
            assignment = rng.choice(assignments)
            skill = rng.choice(skills)
            service = Service.objects.create(
                assignment=assignment,
                description=rng.choice(SERVICE_DESCRIPTIONS.get(skill.name, [""])),
                skill=skill,
                period_source="ASSIGNMENT",
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            all_services.append(service)

        self.stdout.write(f"Services: {len(all_services)}")

        # ── 8. Placements ────────────────────────────────────────────────
        placeable_services = list(all_services)
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
