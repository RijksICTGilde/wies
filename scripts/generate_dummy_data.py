"""Generate representative dummy data for the Wies project.

Fetches real organization hierarchy from organisaties.overheid.nl and generates
colleagues, assignments, services, and placements with realistic Dutch names
and government project names.

Usage:
    python scripts/generate_dummy_data.py            # Full dataset → full_dummy_data.json
    python scripts/generate_dummy_data.py --small     # Small dataset → base_dummy_data.json
"""

import argparse
import json
import logging
import random
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "wies" / "core" / "fixtures"
XML_CACHE_DIR = PROJECT_ROOT / "scripts" / "xml_cache"
ORGANISATIES_OVERHEID_URL = "https://organisaties.overheid.nl/archive/exportOO.xml"

# ── Target counts (full) ─────────────────────────────────────────────────────
NUM_COLLEAGUES = 800
NUM_ASSIGNMENTS = 530
NUM_PLACEMENTS = 800

# ── Target counts (small) ────────────────────────────────────────────────────
SMALL_NUM_COLLEAGUES = 50
SMALL_NUM_ASSIGNMENTS = 30
SMALL_NUM_PLACEMENTS = 50

# ── Distribution settings ─────────────────────────────────────────────────────
ACTIVE_RATIO = 0.85
RIJKSOVERHEID_RATIO = 0.90

ASSIGNMENT_STATUS_WEIGHTS = {"INGEVULD": 70, "VACATURE": 20, "LEAD": 10}
SOURCE_WEIGHTS = {"otys_iir": 85, "wies": 15}
SERVICE_SKILL_PROBABILITY = 0.9
SINGLE_PLACEMENT_THRESHOLD = 0.80
DOUBLE_PLACEMENT_THRESHOLD = 0.95

# ── Hardcoded ministries for --small mode (no XML fetch needed) ───────────────
SMALL_ORGANIZATIONS = [
    (1, "Algemene Zaken", "Ministerie van Algemene Zaken"),
    (2, "Binnenlandse Zaken en Koninkrijksrelaties", "Ministerie van Binnenlandse Zaken en Koninkrijksrelaties"),
    (3, "Buitenlandse Zaken", "Ministerie van Buitenlandse Zaken"),
    (4, "Defensie", "Ministerie van Defensie"),
    (5, "Economische Zaken", "Ministerie van Economische Zaken"),
    (6, "Financiën", "Ministerie van Financiën"),
    (7, "Infrastructuur en Waterstaat", "Ministerie van Infrastructuur en Waterstaat"),
    (8, "Justitie en Veiligheid", "Ministerie van Justitie en Veiligheid"),
    (9, "Onderwijs, Cultuur en Wetenschap", "Ministerie van Onderwijs, Cultuur en Wetenschap"),
    (10, "Sociale Zaken en Werkgelegenheid", "Ministerie van Sociale Zaken en Werkgelegenheid"),
    (11, "Volksgezondheid, Welzijn en Sport", "Ministerie van Volksgezondheid, Welzijn en Sport"),
    # A few child orgs for hierarchy testing
    (12, "Belastingdienst", "Belastingdienst"),
    (13, "Rijkswaterstaat", "Rijkswaterstaat"),
    (14, "RIVM", "RIVM"),
    (15, "Dienst Justitiële Inrichtingen", "Dienst Justitiële Inrichtingen"),
]
SMALL_ORG_PARENTS = {12: 6, 13: 7, 14: 11, 15: 8}  # child_pk → parent_pk

# ── XML namespace (copied from wies/core/services/organizations.py) ───────────
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}

# ── Skills (preserved from current fixture) ───────────────────────────────────
SKILLS = [
    (1, "Backend development"),
    (2, "Frontend development"),
    (3, "Product owner"),
    (4, "UX designer"),
    (5, "AI Consultant"),
    (6, "AI Jurist"),
    (7, "Researcher"),
    (8, "Data engineer"),
    (9, "Project leader"),
    (10, "(Interim) Manager"),
    (11, "Procesbegeleider"),
    (12, "Organisatieadviseur"),
    (13, "Programmamanager"),
    (14, "Beleidsadviseur"),
    (15, "Kwartiermaker"),
    (16, "Verandermanager"),
    (17, "I-Adviseur"),
    (18, "CIO"),
    (19, "Solution Architect"),
    (20, "Cybersecurity Specialist"),
    (21, "Data Architect"),
    (22, "Privacy Officer"),
    (23, "Scrum Master"),
    (24, "Business Analist"),
    (25, "DevOps Engineer"),
    (27, "Test Manager"),
    (28, "Information Manager"),
    (29, "Process Analyst"),
]
SKILL_PKS = [pk for pk, _ in SKILLS]

# ── Dutch name pools ──────────────────────────────────────────────────────────
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

# ── Assignment name building blocks ──────────────────────────────────────────
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


# ── XML parsing (adapted from wies/core/services/organizations.py) ───────────


def build_source_url(system_id: str, name: str) -> str:
    if not system_id:
        return ""
    slug = re.sub(r"[^\w\-]", "_", name)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"https://organisaties.overheid.nl/{system_id}/{slug}/"


def parse_organization_element(org_elem: ET.Element) -> dict | None:
    """Parse a single organization element from XML (recursive)."""
    name = org_elem.findtext("p:naam", "", NS).strip()

    einddatum_elem = org_elem.find("p:eindDatum", NS)
    if einddatum_elem is not None and einddatum_elem.text:
        try:
            einddatum = datetime.fromisoformat(einddatum_elem.text.strip()).date()
            if einddatum < datetime.now(tz=UTC).date():
                return None
        except ValueError:
            pass

    org_type_names = [t.text for t in org_elem.findall("p:types/p:type", NS) if t.text]
    tooi = org_elem.get(f"{{{NS['p']}}}resourceIdentifierTOOI", "")
    system_id = org_elem.get(f"{{{NS['p']}}}systeemId", org_elem.get("systeemId", ""))

    label = name
    for org_type in org_type_names:
        if org_type.lower() == "ministerie" and not name.startswith("Ministerie"):
            label = f"Ministerie van {name}"

    related_ministry_tooi = ""
    related_ministry_elem = org_elem.find("p:relatieMetMinisterie", NS)
    if related_ministry_elem is not None:
        related_ministry_tooi = related_ministry_elem.get(f"{{{NS['p']}}}resourceIdentifierTOOI", "")

    abbreviations = [a.text.strip() for a in org_elem.findall("p:afkorting", NS) if a.text]
    source_url = build_source_url(system_id, name)

    children = []
    for child_elem in org_elem.findall("p:organisaties/p:organisatie", NS):
        child_data = parse_organization_element(child_elem)
        if child_data:
            children.append(child_data)

    return {
        "name": name,
        "system_id": system_id,
        "label": label,
        "org_type_names": org_type_names,
        "tooi_identifier": tooi if tooi else None,
        "abbreviations": abbreviations,
        "source_url": source_url if source_url else None,
        "children": children,
        "related_ministry_tooi": related_ministry_tooi,
    }


def parse_xml_hierarchical(xml_content: bytes) -> list[dict]:
    """Parse organizations from XML export with hierarchy."""
    root = ET.fromstring(xml_content)  # noqa: S314
    organizations = []
    for org in root.findall("p:organisaties/p:organisatie", NS):
        org_data = parse_organization_element(org)
        if org_data is not None:
            organizations.append(org_data)
    return organizations


# ── XML fetching with cache ───────────────────────────────────────────────────


def fetch_xml() -> bytes:
    cache_max_age_hours = 24
    cache_file = XML_CACHE_DIR / "exportOO.xml"
    if cache_file.exists():
        age_hours = (datetime.now(tz=UTC).timestamp() - cache_file.stat().st_mtime) / 3600
        if age_hours < cache_max_age_hours:
            logger.info("Using cached XML (%s)", cache_file)
            return cache_file.read_bytes()

    logger.info("Fetching XML from %s ...", ORGANISATIES_OVERHEID_URL)
    response = requests.get(ORGANISATIES_OVERHEID_URL, timeout=120)
    response.raise_for_status()

    XML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(response.content)
    logger.info("Cached XML to %s", cache_file)
    return response.content


# ── Organization flattening ───────────────────────────────────────────────────


def flatten_org_tree(
    org_data: dict,
    parent_pk: int | None,
    pk_counter: list[int],
    type_registry: dict[str, int],
    type_pk_counter: list[int],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Flatten hierarchical org tree into fixture records.

    Returns (org_units, org_types, org_type_through_records).
    """
    current_pk = pk_counter[0]
    pk_counter[0] += 1

    org_units = []
    org_types = []

    # Register organization types
    for type_name in org_data.get("org_type_names", []):
        if type_name not in type_registry:
            tp = type_pk_counter[0]
            type_pk_counter[0] += 1
            type_registry[type_name] = tp
            org_types.append(
                {
                    "model": "core.organizationtype",
                    "pk": tp,
                    "fields": {"name": type_name.lower(), "label": type_name},
                }
            )

    org_units.append(
        {
            "model": "core.organizationunit",
            "pk": current_pk,
            "fields": {
                "name": org_data["name"],
                "label": org_data["label"],
                "abbreviations": org_data.get("abbreviations", []),
                "tooi_identifier": org_data.get("tooi_identifier"),
                "oin_number": None,
                "system_id": org_data.get("system_id", ""),
                "source_url": org_data.get("source_url") or "",
                "parent": parent_pk,
                "related_ministry_tooi": org_data.get("related_ministry_tooi", ""),
            },
        }
    )

    org_type_through = [
        {"org_unit_pk": current_pk, "org_type_pk": type_registry[type_name]}
        for type_name in org_data.get("org_type_names", [])
    ]

    for child in org_data.get("children", []):
        c_units, c_types, c_through = flatten_org_tree(child, current_pk, pk_counter, type_registry, type_pk_counter)
        org_units.extend(c_units)
        org_types.extend(c_types)
        org_type_through.extend(c_through)

    return org_units, org_types, org_type_through


# ── Helpers ───────────────────────────────────────────────────────────────────


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


def active_dates(rng: random.Random, ref: date) -> tuple[str, str]:
    """Return (start, end) ISO strings where end > ref."""
    start = ref + timedelta(days=rng.randint(-730, 180))
    duration = rng.randint(90, 730)
    end = start + timedelta(days=duration)
    if end <= ref:
        end = ref + timedelta(days=rng.randint(30, 365))
    return start.isoformat(), end.isoformat()


def historic_dates(rng: random.Random, ref: date) -> tuple[str, str]:
    """Return (start, end) ISO strings where end < ref."""
    end = ref + timedelta(days=rng.randint(-1095, -30))
    duration = rng.randint(90, 540)
    start = end - timedelta(days=duration)
    return start.isoformat(), end.isoformat()


# ── Organization distribution ─────────────────────────────────────────────────


def classify_orgs(
    org_units: list[dict],
    org_type_through: list[dict],
    type_registry: dict[str, int],
) -> tuple[list[int], list[int]]:
    """Split org PKs into (rijksoverheid_non_root, other).

    rijksoverheid_non_root: orgs within ministry trees but not the top-level ministry.
    other: everything else (agentschappen, adviescolleges, etc.).
    """
    ministry_type_pk = type_registry.get("Ministerie")
    if ministry_type_pk is None:
        # Fallback: all orgs are candidates
        all_pks = [o["pk"] for o in org_units]
        return all_pks, []

    ministry_root_pks = {t["org_unit_pk"] for t in org_type_through if t["org_type_pk"] == ministry_type_pk}

    children_map: dict[int, list[int]] = {}
    for org in org_units:
        parent = org["fields"]["parent"]
        if parent is not None:
            children_map.setdefault(parent, []).append(org["pk"])

    def descendants(pk: int) -> set[int]:
        result = set()
        for child in children_map.get(pk, []):
            result.add(child)
            result.update(descendants(child))
        return result

    rijks_all = set()
    for mpk in ministry_root_pks:
        rijks_all.add(mpk)
        rijks_all.update(descendants(mpk))

    # Prefer non-root orgs for assignment placement
    rijks_non_root = [pk for pk in rijks_all if pk not in ministry_root_pks]
    if not rijks_non_root:
        rijks_non_root = list(rijks_all)

    other = [o["pk"] for o in org_units if o["pk"] not in rijks_all]

    return rijks_non_root, other


# ── Main generation ───────────────────────────────────────────────────────────


def generate(seed: int = 42, *, small: bool = False) -> list[dict]:  # noqa: C901
    rng = random.Random(seed)  # noqa: S311
    today = datetime.now(tz=UTC).date()
    fixture: list[dict] = []

    num_colleagues = SMALL_NUM_COLLEAGUES if small else NUM_COLLEAGUES
    num_assignments = SMALL_NUM_ASSIGNMENTS if small else NUM_ASSIGNMENTS
    num_placements = SMALL_NUM_PLACEMENTS if small else NUM_PLACEMENTS

    # ── 1. Skills ─────────────────────────────────────────────────────────
    for pk, name in SKILLS:
        fixture.append({"model": "core.skill", "pk": pk, "fields": {"name": name}})
    logger.info("Skills: %d", len(SKILLS))

    # ── 2. Organizations ──────────────────────────────────────────────────
    if small:
        # Use hardcoded ministries — no network needed
        all_org_units = []
        all_org_types = [
            {"model": "core.organizationtype", "pk": 1, "fields": {"name": "ministerie", "label": "Ministerie"}},
        ]
        all_org_type_through = []
        type_registry = {"Ministerie": 1}

        for pk, name, label in SMALL_ORGANIZATIONS:
            parent = SMALL_ORG_PARENTS.get(pk)
            all_org_units.append(
                {
                    "model": "core.organizationunit",
                    "pk": pk,
                    "fields": {
                        "name": name,
                        "label": label,
                        "abbreviations": [],
                        "tooi_identifier": None,
                        "oin_number": None,
                        "system_id": "",
                        "source_url": "",
                        "parent": parent,
                        "related_ministry_tooi": "",
                    },
                }
            )
            if parent is None:  # top-level = ministry
                all_org_type_through.append({"org_unit_pk": pk, "org_type_pk": 1})

        logger.info("Using %d hardcoded organizations (small mode)", len(SMALL_ORGANIZATIONS))
    else:
        # Fetch real organization hierarchy from XML
        xml_content = fetch_xml()
        org_tree = parse_xml_hierarchical(xml_content)
        logger.info("Parsed %d root organizations from XML", len(org_tree))

        pk_counter = [1]
        type_pk_counter = [1]
        type_registry: dict[str, int] = {}

        all_org_units = []
        all_org_types = []
        all_org_type_through = []

        for root_org in org_tree:
            units, types, through = flatten_org_tree(root_org, None, pk_counter, type_registry, type_pk_counter)
            all_org_units.extend(units)
            all_org_types.extend(types)
            all_org_type_through.extend(through)

    fixture.extend(all_org_types)
    fixture.extend(all_org_units)

    for i, through in enumerate(all_org_type_through, start=1):
        fixture.append(
            {
                "model": "core.organizationunit_organization_types",
                "pk": i,
                "fields": {
                    "organizationunit_id": through["org_unit_pk"],
                    "organizationtype_id": through["org_type_pk"],
                },
            }
        )

    logger.info("Organization units: %d", len(all_org_units))
    logger.info("Organization types: %d", len(all_org_types))

    rijks_pks, other_pks = classify_orgs(all_org_units, all_org_type_through, type_registry)
    logger.info("Rijksoverheid orgs (non-root): %d, Other orgs: %d", len(rijks_pks), len(other_pks))

    # ── 3. Colleagues ─────────────────────────────────────────────────────
    used_emails: set[str] = set()
    for pk in range(1, num_colleagues + 1):
        name = generate_name(rng)
        base = sanitize_email(name)
        email = f"{base}@rijksoverheid.nl"
        # Ensure unique email
        if email in used_emails:
            email = f"{base}.{pk}@rijksoverheid.nl"
        used_emails.add(email)

        num_skills = rng.randint(1, 3)
        skills = sorted(rng.sample(SKILL_PKS, num_skills))

        fixture.append(
            {
                "model": "core.colleague",
                "pk": pk,
                "fields": {
                    "name": name,
                    "email": email,
                    "skills": skills,
                    "labels": [],
                    "source": weighted_choice(rng, SOURCE_WEIGHTS),
                    "source_id": "",
                },
            }
        )
    logger.info("Colleagues: %d", num_colleagues)

    # ── 4. Assignments ────────────────────────────────────────────────────
    assignment_dates: dict[int, tuple[str, str]] = {}
    assignment_statuses: dict[int, str] = {}

    for pk in range(1, num_assignments + 1):
        status = weighted_choice(rng, ASSIGNMENT_STATUS_WEIGHTS)
        is_active = rng.random() < ACTIVE_RATIO
        start, end = active_dates(rng, today) if is_active else historic_dates(rng, today)

        assignment_dates[pk] = (start, end)
        assignment_statuses[pk] = status

        fixture.append(
            {
                "model": "core.assignment",
                "pk": pk,
                "fields": {
                    "name": generate_assignment_name(rng),
                    "start_date": start,
                    "end_date": end,
                    "status": status,
                    "extra_info": "",
                    "owner": rng.randint(1, num_colleagues),
                    "source": weighted_choice(rng, SOURCE_WEIGHTS),
                    "source_id": "",
                },
            }
        )
    logger.info("Assignments: %d", num_assignments)

    # ── 5. Assignment ↔ Organization links ────────────────────────────────
    for pk in range(1, num_assignments + 1):
        if rng.random() < RIJKSOVERHEID_RATIO and rijks_pks:
            org_pk = rng.choice(rijks_pks)
        elif other_pks:
            org_pk = rng.choice(other_pks)
        else:
            org_pk = rng.choice(rijks_pks) if rijks_pks else 1

        fixture.append(
            {
                "model": "core.assignmentorganizationunit",
                "pk": pk,
                "fields": {"assignment": pk, "organization": org_pk},
            }
        )

    # ── 6. Services ───────────────────────────────────────────────────────
    # Distribute services so most assignments get 1, some get 2-3
    service_pk = 1
    assignment_service_pks: dict[int, list[int]] = {pk: [] for pk in range(1, num_assignments + 1)}

    # First pass: give each assignment at least 1 service
    assignment_order = list(range(1, num_assignments + 1))
    rng.shuffle(assignment_order)

    for a_pk in assignment_order:
        skill_pk = rng.choice(SKILL_PKS) if rng.random() < SERVICE_SKILL_PROBABILITY else None
        fixture.append(
            {
                "model": "core.service",
                "pk": service_pk,
                "fields": {
                    "assignment": a_pk,
                    "description": rng.choice(SERVICE_DESCRIPTIONS),
                    "skill": skill_pk,
                    "period_source": "ASSIGNMENT",
                    "source": weighted_choice(rng, SOURCE_WEIGHTS),
                    "source_id": "",
                },
            }
        )
        assignment_service_pks[a_pk].append(service_pk)
        service_pk += 1

    # Second pass: add extra services to INGEVULD assignments so we have enough
    # for ~800 placements (VACATURE/LEAD assignments don't need placements)
    ingevuld_pks = [pk for pk, st in assignment_statuses.items() if st == "INGEVULD"]
    target_placeable = num_placements + 50
    current_placeable = sum(
        len(s_pks) for a_pk, s_pks in assignment_service_pks.items() if assignment_statuses[a_pk] == "INGEVULD"
    )
    while current_placeable < target_placeable:
        a_pk = rng.choice(ingevuld_pks)
        skill_pk = rng.choice(SKILL_PKS) if rng.random() < SERVICE_SKILL_PROBABILITY else None
        fixture.append(
            {
                "model": "core.service",
                "pk": service_pk,
                "fields": {
                    "assignment": a_pk,
                    "description": rng.choice(SERVICE_DESCRIPTIONS),
                    "skill": skill_pk,
                    "period_source": "ASSIGNMENT",
                    "source": weighted_choice(rng, SOURCE_WEIGHTS),
                    "source_id": "",
                },
            }
        )
        assignment_service_pks[a_pk].append(service_pk)
        service_pk += 1
        current_placeable += 1

    total_services = service_pk - 1
    logger.info("Services: %d", total_services)

    # ── 7. Placements ─────────────────────────────────────────────────────
    # Only INGEVULD assignments get placements
    placeable_service_pks = []
    for a_pk, s_pks in assignment_service_pks.items():
        if assignment_statuses[a_pk] == "INGEVULD":
            placeable_service_pks.extend(s_pks)
    rng.shuffle(placeable_service_pks)

    # Determine how many placements each colleague gets
    colleague_targets: dict[int, int] = {}
    for c_pk in range(1, num_colleagues + 1):
        r = rng.random()
        if r < SINGLE_PLACEMENT_THRESHOLD:
            colleague_targets[c_pk] = 1
        elif r < DOUBLE_PLACEMENT_THRESHOLD:
            colleague_targets[c_pk] = 2
        else:
            colleague_targets[c_pk] = rng.randint(3, 4)

    placement_pk = 1
    service_idx = 0

    # Shuffle colleagues to avoid bias
    colleague_order = list(range(1, num_colleagues + 1))
    rng.shuffle(colleague_order)

    for c_pk in colleague_order:
        for _ in range(colleague_targets[c_pk]):
            if service_idx >= len(placeable_service_pks) or placement_pk > num_placements:
                break
            s_pk = placeable_service_pks[service_idx]
            service_idx += 1

            fixture.append(
                {
                    "model": "core.placement",
                    "pk": placement_pk,
                    "fields": {
                        "colleague": c_pk,
                        "service": s_pk,
                        "period_source": "SERVICE",
                        "specific_start_date": None,
                        "specific_end_date": None,
                        "source": weighted_choice(rng, SOURCE_WEIGHTS),
                        "source_id": "",
                    },
                }
            )
            placement_pk += 1

    total_placements = placement_pk - 1
    logger.info("Placements: %d", total_placements)

    return fixture


def main():
    parser = argparse.ArgumentParser(description="Generate dummy data for Wies")
    parser.add_argument(
        "--small",
        action="store_true",
        help="Generate small dataset (~50 records each) with hardcoded orgs (no network needed)",
    )
    args = parser.parse_args()

    fixture = generate(small=args.small)

    output_path = FIXTURES_DIR / ("base_dummy_data.json" if args.small else "full_dummy_data.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=2, ensure_ascii=False)

    logger.info("\nWritten to %s", output_path)

    # Summary
    counts = Counter(r["model"] for r in fixture)
    logger.info("\nSummary:")
    for model, count in sorted(counts.items()):
        logger.info("  %-50s %d", model, count)
    logger.info("  %-50s %d", "TOTAL", len(fixture))


if __name__ == "__main__":
    main()
