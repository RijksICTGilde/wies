"""Generate dummy data for the Wies project.

One generator, two size profiles (see ``PROFILES``):

- ``full`` — a large dataset that syncs real organizations from
  organisaties.overheid.nl. Needs the network.
- ``base`` — a small, self-contained dataset that seeds a handful of
  organizations locally. Works offline, so it drives ``just setup`` and the
  /staff/ "load base data" button. It replaces the old
  ``base_dummy_data.json`` fixture: everything the fixture shipped (colleagues
  with a user+role+labels, all three label categories, assignments, services,
  placements, org units, events) is generated here with dates relative to
  today, so it never ages out the way a fixed-date snapshot did.

The generator clears the dummy data it owns before regenerating, so running it
a second time (a /staff/ reseed onto an environment that already has data)
regenerates cleanly instead of piling up duplicates.

Usage:
    python manage.py load_dummy_data --profile base   # small, offline
    python manage.py load_dummy_data --profile full   # large, network sync
    python manage.py load_full_data                   # alias for --profile full
"""

import logging
import random
import re
from dataclasses import dataclass
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    ContractPeriod,
    Event,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    Suborganization,
)
from wies.core.roles import BDM_GROUP_NAME
from wies.core.services.events import create_event
from wies.core.services.organizations import get_org_descendant_ids, sync_organizations

logger = logging.getLogger(__name__)


# ── Size profiles ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Profile:
    """A named size + org-source combination for the generator."""

    num_colleagues: int
    num_assignments: int
    num_placements: int
    # base seeds a small org hierarchy locally (offline); full syncs the real
    # organizations from organisaties.overheid.nl over the network.
    seed_orgs_locally: bool


PROFILES = {
    # base counts are tuned to satisfy the occupancy expectations in
    # test_base_dummy_data.py (≥20 consultant placements, 50-85% placed, both
    # urgency bands, a minority of bench rows with planned work).
    "base": Profile(num_colleagues=50, num_assignments=32, num_placements=60, seed_orgs_locally=True),
    "full": Profile(num_colleagues=800, num_assignments=530, num_placements=800, seed_orgs_locally=False),
}

# ── Distribution settings ────────────────────────────────────────────────────
ACTIVE_RATIO = 0.85
RIJKSOVERHEID_RATIO = 0.90

SOURCE_WEIGHTS = {"otys_iir": 50, "wies": 50}
# Role mix for the dummy users: most consultants, some BDMs, a few beheerders.
# Assignment owners are drawn only from the BDM colleagues, matching production
# where the owner is a Business Development Manager.
ROLE_WEIGHTS = {"Consultant": 80, "Business Development Manager": 15, "Beheerder": 5}
# Contract hours per week: mostly 36, the rijksoverheid norm.
CONTRACT_HOURS_WEIGHTS = {36: 50, 32: 25, 40: 15, 24: 10}
# Hours per week on a role. None: the role has no hours recorded yet, which the
# Bezetting page must keep handling.
ROLE_HOURS_WEIGHTS = {None: 15, 8: 5, 16: 10, 24: 20, 32: 25, 36: 20, 40: 5}
SINGLE_PLACEMENT_THRESHOLD = 0.80
DOUBLE_PLACEMENT_THRESHOLD = 0.95
MULTI_LABEL_PROBABILITY = 0.3
MAX_LABELS_PER_CATEGORY = 2
# Roughly half the assignments also get a second (update) audit event.
EVENT_UPDATE_PROBABILITY = 0.5

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


# ── Offline organizations (base profile) ─────────────────────────────────────
# A small, fixed hierarchy so the base profile works without the network sync.
# Names and TOOI identifiers mirror the real ministries so the data reads true;
# the type name "ministerie" matches what the live sync stores (lowercase), so
# classify_orgs_from_db() behaves the same offline as online.
BASE_MINISTRIES = [
    ("Algemene Zaken", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1010"),
    ("Binnenlandse Zaken en Koninkrijksrelaties", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1034"),
    ("Buitenlandse Zaken", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1013"),
    ("Defensie", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1018"),
    ("Economische Zaken", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1045"),
    ("Financiën", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1090"),
    ("Infrastructuur en Waterstaat", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1130"),
    ("Justitie en Veiligheid", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1058"),
    ("Onderwijs, Cultuur en Wetenschap", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1109"),
    ("Sociale Zaken en Werkgelegenheid", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1073"),
    ("Volksgezondheid, Welzijn en Sport", "https://identifier.overheid.nl/tooi/id/ministerie/mnre1025"),
]
# (name, tooi, parent_ministry_name or None) — the agentschappen/onderdelen.
BASE_SUBORGS = [
    ("Directoraat-generaal Belastingdienst", "https://identifier.overheid.nl/tooi/id/oorg/oorg12368", "Financiën"),
    ("Rijkswaterstaat", "https://identifier.overheid.nl/tooi/id/oorg/oorg10004", "Infrastructuur en Waterstaat"),
    ("Rijksinstituut voor Volksgezondheid en Milieu", "https://identifier.overheid.nl/tooi/id/oorg/oorg10123", None),
    (
        "Dienst Justitiële Inrichtingen",
        "https://identifier.overheid.nl/tooi/id/oorg/oorg10114",
        "Justitie en Veiligheid",
    ),
]


def seed_base_organizations() -> None:
    """Create a small fixed org hierarchy for the offline base profile."""
    ministerie, _ = OrganizationType.objects.get_or_create(name="ministerie", defaults={"label": "Ministerie"})
    onderdeel, _ = OrganizationType.objects.get_or_create(
        name="organisatieonderdeel", defaults={"label": "Organisatieonderdeel"}
    )

    ministries: dict[str, OrganizationUnit] = {}
    for name, tooi in BASE_MINISTRIES:
        unit = OrganizationUnit.objects.create(name=name, label=f"Ministerie van {name}", tooi_identifier=tooi)
        unit.organization_types.add(ministerie)
        ministries[name] = unit

    for name, tooi, parent_name in BASE_SUBORGS:
        unit = OrganizationUnit.objects.create(
            name=name, label=name, tooi_identifier=tooi, parent=ministries.get(parent_name)
        )
        unit.organization_types.add(onderdeel)


def assign_roles(rng: random.Random, count: int) -> list[str]:
    """A shuffled list of ``count`` role names in roughly ``ROLE_WEIGHTS``
    proportion, but guaranteeing at least one of every role when ``count``
    allows it — a weighted per-item draw can leave a rare role (Beheerder)
    empty at the small base-profile size."""
    roles = list(ROLE_WEIGHTS)
    if count <= len(roles):
        return roles[:count]

    total = sum(ROLE_WEIGHTS.values())
    # One of each first, then fill the remainder by proportion.
    counts = dict.fromkeys(roles, 1)
    remaining = count - len(roles)
    for role in roles:
        counts[role] += round(remaining * ROLE_WEIGHTS[role] / total)
    # Rounding can drift by a few; correct on the majority role.
    counts[roles[0]] += count - sum(counts.values())

    result = [role for role, n in counts.items() for _ in range(n)]
    rng.shuffle(result)
    return result


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


def _seed_all_label_categories() -> None:
    """Ensure every label category + its labels exist, self-contained.

    Production seeds Expertise/Thema from ``setup``; the offline base profile
    seeds them here too so it does not depend on ``setup`` having run. Subgroep
    is the demo-only "gilde" category the Bezetting page filters on.
    """
    from wies.core.models import DEFAULT_LABELS  # noqa: PLC0415 — avoid a heavy import at module load

    for category_name, category_vals in DEFAULT_LABELS.items():
        category, _ = LabelCategory.objects.get_or_create(
            name=category_name, defaults={"color": category_vals["color"]}
        )
        for label_name in category_vals["labels"]:
            Label.objects.get_or_create(name=label_name, category=category)

    subgroep, _ = LabelCategory.objects.get_or_create(name="Subgroep", defaults={"color": "#DCE3EA"})
    for label_name in ("ICT", "AI"):
        Label.objects.get_or_create(name=label_name, category=subgroep)


def generate(profile: Profile, *, write=lambda msg: None) -> None:  # noqa: C901
    """Generate a full set of dummy data for the given size profile.

    Clears the dummy data it owns first, so a second run (e.g. a /staff/ reseed)
    regenerates cleanly instead of duplicating. Users are kept across runs and
    reused by email, since deleting them would orphan logins.
    """
    rng = random.Random(42)  # noqa: S311
    today = timezone.now().date()

    # Role groups are needed for the per-colleague user role; seed them if this
    # runs standalone.
    from wies.core.roles import setup_roles  # noqa: PLC0415 — local import avoids a heavy import at module load

    setup_roles()

    # ── 0. Clean up existing dummy data ──────────────────────────────
    write("Cleaning up existing data...")
    Placement.objects.all().delete()
    Service.objects.all().delete()
    # Assignment events carry the assignment PK in object_id (not a FK), so they
    # do not cascade; clear them here or they pile up over reseeds.
    Event.objects.filter(object_type="Assignment").delete()
    Assignment.objects.all().delete()
    Colleague.objects.all().delete()
    OrganizationUnit.objects.update(parent=None)
    OrganizationUnit.objects.all().delete()

    # ── 1. Organizations ─────────────────────────────────────────────
    if profile.seed_orgs_locally:
        write("Seeding a small organization hierarchy locally (offline)...")
        seed_base_organizations()
    else:
        write("Syncing organizations from organisaties.overheid.nl...")
        result = sync_organizations()
        write(
            f"  Sync: created={result.created}, updated={result.updated}, "
            f"unchanged={result.unchanged}, deactivated={result.deactivated}"
        )

    org_count = OrganizationUnit.objects.filter(end_date__isnull=True).count()
    write(f"  Active organizations: {org_count}")

    # ── 2. Skills ────────────────────────────────────────────────────
    skills = []
    for name in SKILLS:
        skill, _ = Skill.objects.get_or_create(name=name)
        skills.append(skill)
    write(f"Skills: {len(skills)}")

    # ── 3. Classify orgs for assignment distribution ─────────────────
    rijks_pks, other_pks = classify_orgs_from_db()
    write(f"Rijksoverheid orgs (non-root): {len(rijks_pks)}, Other orgs: {len(other_pks)}")

    # ── 4. Colleagues ────────────────────────────────────────────────
    used_emails: set[str] = set()
    colleagues = []
    for i in range(1, profile.num_colleagues + 1):
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
    write(f"Colleagues: {len(colleagues)}")

    # ── 4b. Colleague labels ─────────────────────────────────────────
    _seed_all_label_categories()
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
        write("Colleague labels assigned")

    # ── 4c. Colleague suborganization (exactly one per colleague) ────
    suborganizations = list(Suborganization.objects.all())
    if suborganizations:
        for colleague in colleagues:
            colleague.suborganization = rng.choice(suborganizations)
            colleague.save(update_fields=["suborganization"])
        write("Colleague suborganizations assigned")

    # ── 4d. Colleague user + role (most consultants, some BDM, few beheerder) ──
    user_model = get_user_model()
    role_groups = {name: Group.objects.get(name=name) for name in ROLE_WEIGHTS}
    role_counts = dict.fromkeys(ROLE_WEIGHTS, 0)
    roles = assign_roles(rng, len(colleagues))
    bdm_colleagues = []
    for colleague, role in zip(colleagues, roles, strict=True):
        first_name, _, last_name = colleague.name.partition(" ")
        # A previous run may have left a user with this email (colleagues are
        # deleted and recreated, users are not); reuse it instead of colliding.
        user, _ = user_model.objects.get_or_create(
            email=colleague.email, defaults={"first_name": first_name, "last_name": last_name}
        )
        colleague.user = user
        colleague.save(update_fields=["user"])
        user.groups.add(role_groups[role])
        role_counts[role] += 1
        if role == BDM_GROUP_NAME:
            bdm_colleagues.append(colleague)
    write("Colleague roles: " + ", ".join(f"{role_counts[n]} {n}" for n in ROLE_WEIGHTS))

    # ── 4e. Contract periods ─────────────────────────────────────────
    # One running period each, started some time ago; a fifth also has an
    # older, closed period with different hours, so the history has something
    # to show.
    for colleague in colleagues:
        hours = weighted_choice(rng, CONTRACT_HOURS_WEIGHTS)
        started = today - timedelta(days=rng.randint(180, 1100))
        ContractPeriod.objects.create(colleague=colleague, hours_per_week=hours, start_date=started)
        if rng.random() < 0.2:  # noqa: PLR2004 (0.2 = share with a closed earlier period)
            earlier_hours = rng.choice([h for h in CONTRACT_HOURS_WEIGHTS if h != hours])
            ContractPeriod.objects.create(
                colleague=colleague,
                hours_per_week=earlier_hours,
                start_date=started - timedelta(days=rng.randint(365, 900)),
                end_date=started - timedelta(days=1),
            )
    write("Contract periods assigned")

    # ── 5. Assignments ───────────────────────────────────────────────
    assignments = []

    for _ in range(profile.num_assignments):
        is_active = rng.random() < ACTIVE_RATIO
        start, end = active_dates(rng, today) if is_active else historic_dates(rng, today)

        assignment = Assignment.objects.create(
            name=generate_assignment_name(rng),
            start_date=start,
            end_date=end,
            extra_info="",
            # Owners are drawn only from BDM colleagues, matching production
            # where the assignment owner is a Business Development Manager.
            owner=rng.choice(bdm_colleagues),
            source=weighted_choice(rng, SOURCE_WEIGHTS),
            source_id="",
        )
        assignments.append(assignment)
        # A couple of audit events per assignment so the events routes have data.
        create_event(object_type="Assignment", action="create", source="sync", object_id=assignment.id)
        if rng.random() < EVENT_UPDATE_PROBABILITY:
            create_event(
                object_type="Assignment",
                action="update",
                source="sync",
                object_id=assignment.id,
                context={"name": assignment.name},
            )
    write(f"Assignments: {len(assignments)}")

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
            hours_per_week=weighted_choice(rng, ROLE_HOURS_WEIGHTS),
            period_source="ASSIGNMENT",
            source=weighted_choice(rng, SOURCE_WEIGHTS),
            source_id="",
        )
        all_services.append(service)

    # Second pass: add extra services until we have enough for placements
    target_placeable = profile.num_placements + 50
    while len(all_services) < target_placeable:
        assignment = rng.choice(assignments)
        skill = rng.choice(skills)
        service = Service.objects.create(
            assignment=assignment,
            description=rng.choice(SERVICE_DESCRIPTIONS.get(skill.name, [""])),
            skill=skill,
            hours_per_week=weighted_choice(rng, ROLE_HOURS_WEIGHTS),
            period_source="ASSIGNMENT",
            source=weighted_choice(rng, SOURCE_WEIGHTS),
            source_id="",
        )
        all_services.append(service)

    write(f"Services: {len(all_services)}")

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
            if service_idx >= len(placeable_services) or placement_count >= profile.num_placements:
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

    write(f"Placements: {placement_count}")


class Command(BaseCommand):
    help = "Generate the full dummy dataset (network sync). Alias for load_dummy_data --profile full."

    def handle(self, *args, **options):
        generate(PROFILES["full"], write=self.stdout.write)
        self.stdout.write(self.style.SUCCESS("Done!"))
