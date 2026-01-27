"""Organization sync service.

Syncs organizations from organisaties.overheid.nl XML export.
Supports hierarchical import of ministries with their DG's, directies and afdelingen.
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.request import urlopen

from wies.core.models import XML_TYPE_MAPPING, OrganizationUnit

logger = logging.getLogger(__name__)

ORGANISATIES_OVERHEID_URL = "https://organisaties.overheid.nl/archive/exportOO.xml"
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}

# Available root types from organisaties.overheid.nl XML (for --type filter)
AVAILABLE_TYPES = [
    "Adviescollege",
    "Agentschap",
    "Caribisch openbaar lichaam",
    "Gemeenschappelijke regeling",
    "Gemeente",
    "Hoog College van Staat",
    "Kabinet van de Koning",
    "Ministerie",
    "Organisatieonderdeel",
    "Politie en brandweer",
    "Provincie",
    "Rechtspraak",
    "Waterschap",
    "Zelfstandig bestuursorgaan",
]

# Patterns to detect organization type from name
NAME_TYPE_PATTERNS = [
    (re.compile(r"^Directoraat-generaal", re.IGNORECASE), "directoraat_generaal"),
    (re.compile(r"^Programma Directoraat-generaal", re.IGNORECASE), "directoraat_generaal"),
    (re.compile(r"^[Dd]irectie\b"), "directie"),
    (re.compile(r"^[Aa]fdeling\b"), "afdeling"),
]


def detect_type_from_name(name: str, parent_type: str | None) -> str:
    """Detect organization type from name patterns."""
    for pattern, org_type in NAME_TYPE_PATTERNS:
        if pattern.match(name):
            return org_type
    # Default to organisatieonderdeel for nested orgs
    return "organisatieonderdeel"


def build_source_url(systeem_id: str, name: str) -> str:
    """Build URL to organisaties.overheid.nl page."""
    if not systeem_id:
        return ""
    # Replace spaces and special chars with underscores for URL
    slug = re.sub(r"[^\w\-]", "_", name)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"https://organisaties.overheid.nl/{systeem_id}/{slug}/"


@dataclass
class SyncResult:
    """Result of organization sync."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def __add__(self, other: "SyncResult") -> "SyncResult":
        """Combine two SyncResults."""
        return SyncResult(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            unchanged=self.unchanged + other.unchanged,
            errors=self.errors + other.errors,
        )


def parse_organization_element(
    org_elem: ET.Element,
    parent: OrganizationUnit | None = None,
) -> dict:
    """Parse a single organization element from XML.

    Returns dict with organization data, including nested children.
    """
    naam = org_elem.findtext("p:naam", "", NS).strip()
    types = [t.text for t in org_elem.findall("p:types/p:type", NS) if t.text]

    # Get identifiers
    tooi = org_elem.get(f"{{{NS['p']}}}resourceIdentifierTOOI", "")
    systeem_id = org_elem.get(f"{{{NS['p']}}}systeemId", org_elem.get("systeemId", ""))

    # Determine organization type
    our_type = None
    for xml_type in types:
        if xml_type in XML_TYPE_MAPPING:
            our_type = XML_TYPE_MAPPING[xml_type]
            break

    # For nested organizations (Organisatieonderdeel), detect type from name
    if our_type == "organisatieonderdeel" or (our_type is None and parent is not None):
        detected = detect_type_from_name(naam, parent.organization_type if parent else None)
        our_type = detected

    # Skip if we still don't have a type
    if our_type is None:
        return None

    # Add "Ministerie van" prefix if needed
    if our_type == "ministerie" and not naam.startswith("Ministerie"):
        naam = f"Ministerie van {naam}"

    # Get abbreviations
    abbreviations = [a.text.strip() for a in org_elem.findall("p:afkorting", NS) if a.text]

    # Build source URL
    source_url = build_source_url(systeem_id, naam)

    # Parse nested organizations
    children = []
    for child_elem in org_elem.findall("p:organisaties/p:organisatie", NS):
        child_data = parse_organization_element(child_elem, parent=None)  # parent set later
        if child_data:
            children.append(child_data)

    return {
        "name": naam,
        "organization_type": our_type,
        "tooi_identifier": tooi if tooi else None,
        "abbreviations": abbreviations,
        "source_url": source_url if source_url else None,
        "children": children,
    }


def parse_xml_hierarchical(xml_content: bytes, filter_types: list[str] | None = None) -> list[dict]:
    """Parse organizations from XML export with hierarchy.

    Args:
        xml_content: Raw XML bytes
        filter_types: Optional list of root types to include (e.g., ["ministerie"])

    Returns:
        List of organization dicts with nested children
    """
    root = ET.fromstring(xml_content)  # noqa: S314
    organizations = []

    # Find top-level organizations (those with TOOI identifier at root level)
    for org in root.findall("p:organisaties/p:organisatie", NS):
        org_data = parse_organization_element(org)
        if org_data is None:
            continue

        # Filter by type if specified
        if filter_types and org_data["organization_type"] not in filter_types:
            continue

        organizations.append(org_data)

    return organizations


def sync_organization_tree(
    org_data: dict,
    parent: OrganizationUnit | None,
    *,
    dry_run: bool,
) -> SyncResult:
    """Recursively sync an organization and its children.

    Args:
        org_data: Dict with organization data and children
        parent: Parent OrganizationUnit (None for root)
        dry_run: If True, don't apply changes

    Returns:
        SyncResult with counts
    """
    result = SyncResult()
    children = org_data.pop("children", [])

    # Find existing org by TOOI or by name+parent combination
    tooi = org_data.get("tooi_identifier")
    existing = None

    if tooi:
        existing = OrganizationUnit.objects.filter(tooi_identifier=tooi).first()

    if not existing and parent:
        # For nested orgs without TOOI, match by name + parent
        existing = OrganizationUnit.objects.filter(
            name=org_data["name"],
            parent=parent,
        ).first()

    try:
        if existing:
            # Check if any field actually changed
            fields_to_check = ["name", "organization_type", "abbreviations", "source_url"]
            has_changes = any(getattr(existing, k) != org_data.get(k) for k in fields_to_check if k in org_data)
            # Also check if parent changed
            if existing.parent != parent:
                has_changes = True

            if has_changes:
                if not dry_run:
                    for key, value in org_data.items():
                        if key != "tooi_identifier" or value:  # Don't overwrite TOOI with None
                            setattr(existing, key, value)
                    existing.parent = parent
                    existing.save()
                    logger.info("Updated: %s (%s)", org_data["name"], org_data["organization_type"])
                result.updated += 1
            else:
                result.unchanged += 1

            current_org = existing
        else:
            # Create new organization
            if not dry_run:
                current_org = OrganizationUnit.objects.create(parent=parent, **org_data)
                logger.info("Created: %s (%s)", org_data["name"], org_data["organization_type"])
            else:
                current_org = None
            result.created += 1

    except Exception as e:
        error_msg = f"Error processing {org_data.get('name', 'unknown')}: {e}"
        logger.exception(error_msg)
        result.errors.append(error_msg)
        return result

    # Recursively sync children
    for child_data in children:
        child_result = sync_organization_tree(
            child_data,
            parent=current_org if not dry_run else existing,
            dry_run=dry_run,
        )
        result = result + child_result

    return result


def sync_organizations(
    *,
    xml_content: bytes | None = None,
    filter_type: str | None = None,
    dry_run: bool = False,
) -> SyncResult:
    """Sync organizations from XML to database.

    Args:
        xml_content: XML bytes (downloads from URL if not provided)
        filter_type: Only sync this XML type (e.g., "Ministerie")
        dry_run: If True, don't apply changes

    Returns:
        SyncResult with counts
    """
    result = SyncResult()

    # Fetch XML if not provided
    if xml_content is None:
        logger.info("Fetching organizations from %s", ORGANISATIES_OVERHEID_URL)
        with urlopen(ORGANISATIES_OVERHEID_URL, timeout=120) as response:  # noqa: S310
            xml_content = response.read()

    # Determine which types to sync
    filter_types = None
    if filter_type:
        our_type = XML_TYPE_MAPPING.get(filter_type)
        if our_type:
            filter_types = [our_type]
        else:
            result.errors.append(f"Unknown type: {filter_type}")
            return result

    # Parse XML with hierarchy
    organizations = parse_xml_hierarchical(xml_content, filter_types)
    logger.info("Parsed %d root organizations from XML", len(organizations))

    # Sync each organization tree
    for org_data in organizations:
        org_result = sync_organization_tree(org_data, parent=None, dry_run=dry_run)
        result = result + org_result

    return result
