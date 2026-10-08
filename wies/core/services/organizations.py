"""Organization sync service.

Syncs organizations from organisaties.overheid.nl XML export.
Supports hierarchical import of ministries with their DG's, directies and afdelingen.
"""

import io
import logging
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import IO, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from collections.abc import Iterator
from django.db.models import Q
from django.utils import timezone

from wies.core.models import OrganizationType, OrganizationUnit
from wies.core.public_id import parse_public_ids
from wies.core.services.events import create_event

logger = logging.getLogger(__name__)

ORGANISATIES_OVERHEID_URL = "https://organisaties.overheid.nl/archive/exportOO.xml"
# The export's XML namespace ends in a schema version (e.g. ".../export/2.6.13")
# that overheid.nl bumps without notice, so only the prefix is fixed here and
# the full namespace is read from each document.
NS_PREFIX = "https://organisaties.overheid.nl/static/schema/oo/export/"

# Organizations excluded from sync (intelligence services).
# All comparisons are case-insensitive.
EXCLUDED_ORG_NAMES: set[str] = {
    "algemene inlichtingen- en veiligheidsdienst",
    "militaire inlichtingen- en veiligheidsdienst",
}
EXCLUDED_ORG_ABBREVIATIONS: set[str] = {"aivd", "mivd"}

# Types that nest under their ministry. A unit nests only when its MAIN type
# (first-listed = overheid.nl breadcrumb category) is one of these and its
# related_ministry_tooi resolves to a ministry. Others keep their top-level type
# folder in the picker and a plain parent-chain breadcrumb. Used by both the
# picker (build_org_hierarchy) and the breadcrumb (resolve_related_ministry).
NESTED_ORG_TYPES: frozenset[str] = frozenset({"Agentschap", "Zelfstandig bestuursorgaan", "Adviescollege", "Inspectie"})

# Singular → plural display names for organization type group headers.
ORG_TYPE_PLURAL: dict[str, str] = {
    "Adviescollege": "Adviescolleges",
    "Agentschap": "Agentschappen",
    "Caribisch openbaar lichaam": "Caribische openbare lichamen",
    "Externe commissie": "Externe commissies",
    "Gemeente": "Gemeenten",
    "Grensoverschrijdend regionaal samenwerkingsorgaan": "Grensoverschrijdende regionale samenwerkingsorganen",
    "Hoog College van Staat": "Hoge Colleges van Staat",
    "Inspectie": "Inspecties",
    "Interdepartementale commissie": "Interdepartementale commissies",
    "Koepelorganisatie": "Koepelorganisaties",
    "Ministerie": "Ministeries",
    "Openbaar lichaam voor beroep en bedrijf": "Openbare lichamen voor beroep en bedrijf",
    "Organisatie met overheidsbemoeienis": "Organisaties met overheidsbemoeienis",
    "Organisatieonderdeel": "Organisatieonderdelen",
    "Overheidsstichting of -vereniging": "Overheidsstichtingen of -verenigingen",
    "Provinciale Rekenkamer": "Provinciale Rekenkamers",
    "Provincie": "Provincies",
    "Regionaal samenwerkingsorgaan": "Regionale samenwerkingsorganen",
    "Waterschap": "Waterschappen",
    "Zelfstandig bestuursorgaan": "Zelfstandige bestuursorganen",
}


def nested_folder_label(ministry_abbreviation: str, type_label: str) -> str:
    """Label for a scoped nested folder, e.g. "Adviescolleges van BZ".

    ``ministry_abbreviation`` is the ministry's abbreviation (every ministry has
    one; the callers fall back to the full label only if it is ever missing).

    One recognizable plain string shared by the picker folder (get_org_tree
    JSON → org_tree.js), its selection token (tree_state.js) and the active
    chip (_org_chip_data). Plain text so it needs no aria wiring across the
    web-component shadow boundary.
    """
    return f"{ORG_TYPE_PLURAL.get(type_label, type_label)} van {ministry_abbreviation}"


def build_source_url(system_id: str, name: str) -> str:
    """Build URL to organisaties.overheid.nl page."""
    if not system_id:
        return ""
    # Replace spaces and special chars with underscores for URL
    slug = re.sub(r"[^\w\-]", "_", name)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"https://organisaties.overheid.nl/{system_id}/{slug}/"


@dataclass
class SyncResult:
    """Result of organization sync."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    deleted: int = 0
    errors: list[str] = field(default_factory=list)

    def __add__(self, other: SyncResult) -> SyncResult:
        """Combine two SyncResults."""
        return SyncResult(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            unchanged=self.unchanged + other.unchanged,
            deactivated=self.deactivated + other.deactivated,
            deleted=self.deleted + other.deleted,
            errors=self.errors + other.errors,
        )


def parse_organization_element(
    org_elem: ET.Element,
    ns: dict[str, str],
) -> dict | None:
    """Parse a single organization element from XML.

    ``ns`` maps the ``p`` prefix to the document's namespace.

    Returns dict with organization data, including nested children and end_date.
    """
    name = org_elem.findtext("p:naam", "", ns).strip()
    abbreviations = [a.text.strip() for a in org_elem.findall("p:afkorting", ns) if a.text]

    # Parse eindDatum into end_date
    end_date = None
    einddatum_elem = org_elem.find("p:eindDatum", ns)
    if einddatum_elem is not None and einddatum_elem.text:
        try:
            end_date = datetime.fromisoformat(einddatum_elem.text.strip()).date()
        except ValueError:
            # Invalid date format, log and continue processing
            logger.warning("Invalid eindDatum format for organization '%s': %s", name, einddatum_elem.text)

    org_type_names = [t.text for t in org_elem.findall("p:types/p:type", ns) if t.text]

    # Get identifiers
    tooi = org_elem.get(f"{{{ns['p']}}}resourceIdentifierTOOI", "")
    system_id = org_elem.get(f"{{{ns['p']}}}systeemId", org_elem.get("systeemId", ""))

    # Initialize label with default value
    label = name
    for organization_type in org_type_names:
        # Add "Ministerie van" prefix if needed (case-insensitive check)
        if organization_type.lower() == "ministerie" and not name.startswith("Ministerie"):
            label = f"Ministerie van {name}"

    # Get related ministry TOOI from relatieMetMinisterie element's attribute
    related_ministry_tooi = ""
    related_ministry_elem = org_elem.find("p:relatieMetMinisterie", ns)
    if related_ministry_elem is not None:
        related_ministry_tooi = related_ministry_elem.get(f"{{{ns['p']}}}resourceIdentifierTOOI", "")

    # Build source URL
    source_url = build_source_url(system_id, name)

    # Parse nested organizations
    children = []
    for child_elem in org_elem.findall("p:organisaties/p:organisatie", ns):
        child_data = parse_organization_element(child_elem, ns)
        if child_data:
            # Propagate parent's end_date to children without an earlier one
            if end_date is not None:
                child_end = child_data.get("end_date")
                if child_end is None or child_end > end_date:
                    child_data["end_date"] = end_date
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
        "end_date": end_date,
    }


def iter_root_organizations(xml_source: IO[bytes] | str) -> Iterator[dict]:
    """Stream top-level organizations from XML, clearing parsed elements as we go.

    Yields one parsed dict per root <organisatie> and then drops the underlying
    Element so the DOM never grows to hold the full document. Keeps peak memory
    bounded to a single org subtree instead of the entire 30+ MB export.

    Raises ValueError when the document is not an overheid.nl organization export.
    """
    context = ET.iterparse(xml_source, events=("start", "end"))  # noqa: S314 (xml.etree vulnerable to XML attacks) — input is trusted government export from organisaties.overheid.nl
    depth = 0
    root_wrapper: ET.Element | None = None
    ns: dict[str, str] = {}
    org_tag = ""
    orgs_wrapper_tag = ""

    for event, elem in context:
        if not ns:
            # First event is the start of the document root; its namespace
            # (including the schema version) applies to the whole export.
            namespace = elem.tag[1:].partition("}")[0] if elem.tag.startswith("{") else ""
            if not namespace.startswith(NS_PREFIX):
                msg = f"Unexpected XML namespace for organization export: {namespace!r}"
                raise ValueError(msg)
            ns = {"p": namespace}
            org_tag = f"{{{namespace}}}organisatie"
            orgs_wrapper_tag = f"{{{namespace}}}organisaties"

        if event == "start":
            if elem.tag == orgs_wrapper_tag and root_wrapper is None:
                # The first <organisaties> we see is the document-level wrapper
                # whose direct children are the top-level orgs.
                root_wrapper = elem
            if elem.tag == org_tag:
                depth += 1
            continue

        if elem.tag != org_tag:
            continue

        depth -= 1
        if depth != 0:
            # Nested <organisatie> — parent will process it as a child.
            continue

        org_data = parse_organization_element(elem, ns)
        if org_data is not None:
            yield org_data

        # Free the parsed subtree and detach it from the wrapper so processed
        # siblings don't accumulate as the document grows.
        elem.clear()
        if root_wrapper is not None:
            root_wrapper.remove(elem)


def sync_organization_tree(
    org_data: dict,
    parent: OrganizationUnit | None,
    *,
    dry_run: bool,
    seen_ids: set[int] | None = None,
) -> SyncResult:
    """Recursively sync an organization and its children.

    Args:
        org_data: Dict with organization data and children
        parent: Parent OrganizationUnit (None for root)
        dry_run: If True, don't apply changes
        seen_ids: Set to collect IDs of all orgs processed during sync

    Returns:
        SyncResult with counts
    """
    result = SyncResult()
    children = org_data.pop("children", [])
    end_date = org_data.pop("end_date", None)

    # Find existing org by TOOI
    new_tooi = org_data.get("tooi_identifier")
    db_org = None
    if new_tooi:
        db_org = OrganizationUnit.objects.filter(tooi_identifier=new_tooi).first()

    if not db_org:
        # For orgs without TOOI, match by name + parent + types
        candidates = OrganizationUnit.objects.filter(
            name=org_data["name"],
            parent=parent,
        ).prefetch_related("organization_types")

        new_type_names = set(org_data["org_type_names"])

        # Search through all candidates to find one with matching types
        for candidate in candidates:
            # Skip if both have TOOI but they differ (distinct organizations with same name)
            if new_tooi and candidate.tooi_identifier and new_tooi != candidate.tooi_identifier:
                continue
            # Skip if candidate has TOOI but incoming doesn't
            if not new_tooi and candidate.tooi_identifier:
                continue

            db_type_names = set(candidate.organization_types.values_list("name", flat=True))

            # Check if types match
            if not db_type_names or not new_type_names:
                # If either has no types, accept the match (types can be populated/updated)
                db_org = candidate
                break
            if db_type_names == new_type_names:
                # Types match perfectly
                db_org = candidate
                break
            # Otherwise, types differ - keep searching for a better match

    organization_types = []
    if not dry_run:
        for org_type_name in org_data["org_type_names"]:
            organization_type, _ = OrganizationType.objects.get_or_create(
                name=org_type_name, defaults={"label": org_type_name}
            )
            organization_types.append(organization_type)

    try:
        new_org_attributes = {
            "name": org_data["name"],
            "label": org_data["label"],
            "abbreviations": org_data["abbreviations"],
            "related_ministry_tooi": org_data["related_ministry_tooi"],
            "parent": parent,
            "tooi_identifier": new_tooi,
            "oin_number": None,
            "system_id": org_data["system_id"],
            "source_url": org_data["source_url"],
            "end_date": end_date,
            "main_type": organization_types[0] if organization_types else None,
        }

        if db_org:
            changes = {}
            for attribute, new_value in new_org_attributes.items():
                old_value = getattr(db_org, attribute)
                if old_value != new_value:
                    # Ensure JSON-serializable values for event logging
                    if attribute in ("parent", "main_type"):
                        changes[attribute] = {
                            "old": old_value.id if old_value else None,
                            "new": new_value.id if new_value else None,
                        }
                    elif attribute == "end_date":
                        changes[attribute] = {
                            "old": old_value.isoformat() if old_value else None,
                            "new": new_value.isoformat() if new_value else None,
                        }
                    else:
                        changes[attribute] = {"old": old_value, "new": new_value}
                if not dry_run:
                    setattr(db_org, attribute, new_value)

            # The type set is unordered; log a change when its membership differs.
            current_type_pks = set(db_org.organization_types.values_list("pk", flat=True))
            new_type_pks = {obj.pk for obj in organization_types}
            if current_type_pks != new_type_pks:
                changes["organization_types"] = {"old": sorted(current_type_pks), "new": sorted(new_type_pks)}
            if not dry_run:
                db_org.organization_types.set(organization_types)

            if changes:
                if not dry_run:
                    db_org.save()
                    logger.info("Updated: %s", db_org)
                    create_event(
                        object_type="OrganizationUnit",
                        action="update",
                        source="sync",
                        object_id=db_org.id,
                        context={
                            "tooi": db_org.tooi_identifier or "",
                            "changes": changes,
                        },
                    )
                result.updated += 1
            else:
                result.unchanged += 1

            new_org = db_org
        else:
            # Don't create new records for inactive organizations
            if end_date is not None and end_date < timezone.now().date():
                logger.debug("Skipping creation of inactive org: %s", org_data["name"])
                # Still recurse children — they may have existing DB records to update
                for child_data in children:
                    child_result = sync_organization_tree(
                        child_data,
                        parent=None,
                        dry_run=dry_run,
                        seen_ids=seen_ids,
                    )
                    result = result + child_result
                return result

            # Create new organization
            # Log why we're creating instead of matching
            if new_tooi:
                logger.info(
                    "Creating (not found by TOOI): %s | TOOI=%s",
                    org_data["name"],
                    new_tooi,
                )
            elif parent:
                logger.info(
                    "Creating (not found by name+parent+type): %s | parent=%s",
                    org_data["name"],
                    parent.name if parent else None,
                )
            else:
                logger.info("Creating (no TOOI, no matching parent+type): %s", org_data["name"])

            if not dry_run:
                new_org = OrganizationUnit.objects.create(**new_org_attributes)
                new_org.organization_types.set(organization_types)
                logger.info("Created: %s", new_org)
                create_event(
                    object_type="OrganizationUnit",
                    action="create",
                    source="sync",
                    object_id=new_org.id,
                    context={
                        "tooi": new_org.tooi_identifier or "",
                        "name": new_org.name,
                    },
                )
            else:
                new_org = None
            result.created += 1

    except Exception as e:
        error_msg = f"Error processing {org_data.get('name', 'unknown')}: {e}"
        logger.exception(error_msg)
        result.errors.append(error_msg)
        return result

    # Track this org as seen during sync
    if seen_ids is not None and new_org is not None:
        seen_ids.add(new_org.id)

    # Recursively sync children
    for child_data in children:
        child_result = sync_organization_tree(
            child_data,
            parent=db_org if dry_run else new_org,
            dry_run=dry_run,
            seen_ids=seen_ids,
        )
        result = result + child_result

    return result


def sync_organizations(
    *,
    xml_content: bytes | None = None,
    url: str | None = None,
    dry_run: bool = False,
) -> SyncResult:
    """Sync organizations from XML to database.

    Args:
        xml_content: XML bytes (downloads from URL if not provided)
        dry_run: If True, don't apply changes

    Returns:
        SyncResult with counts
    """
    result = SyncResult()
    seen_ids: set[int] = set()
    root_count = 0

    def _sync_stream(org_iter: Iterator[dict]) -> SyncResult:
        nonlocal root_count
        local_result = SyncResult()
        for org_data in org_iter:
            root_count += 1
            org_result = sync_organization_tree(org_data, parent=None, dry_run=dry_run, seen_ids=seen_ids)
            local_result = local_result + org_result
        return local_result

    if xml_content is not None:
        # Test path: caller provided XML bytes. Stream from an in-memory buffer
        # so we still avoid building the full Element tree.
        result = result + _sync_stream(iter_root_organizations(io.BytesIO(xml_content)))
    else:
        fetch_url = url or ORGANISATIES_OVERHEID_URL
        logger.info("Fetching organizations from %s", fetch_url)

        with requests.get(fetch_url, timeout=120, stream=True) as response:
            response.raise_for_status()
            # Stream the response body straight into iterparse so the raw XML
            # is never fully buffered in memory.
            response.raw.decode_content = True
            result = result + _sync_stream(iter_root_organizations(response.raw))

    if root_count == 0:
        # An export without organizations is never valid; reporting it as a
        # successful sync hides a broken source until the data has gone stale.
        msg = "No organizations found in XML export"
        raise ValueError(msg)

    logger.info("Synced %d root organizations from XML (streamed)", root_count)

    # Deactivate external orgs not seen during a full sync
    today = timezone.now().date()
    if not dry_run and seen_ids:
        orgs_to_deactivate = list(
            OrganizationUnit.objects.filter(Q(end_date__isnull=True) | Q(end_date__gt=today))
            .exclude(source_url="")
            .exclude(source_url__isnull=True)
            .exclude(id__in=seen_ids)
            .values_list("id", "tooi_identifier", "name")
        )
        if orgs_to_deactivate:
            OrganizationUnit.objects.filter(id__in=[org[0] for org in orgs_to_deactivate]).update(end_date=today)
            for org_id, tooi, name in orgs_to_deactivate:
                create_event(
                    object_type="OrganizationUnit",
                    action="deactivate",
                    source="sync",
                    object_id=org_id,
                    context={
                        "tooi": tooi or "",
                        "name": name,
                        "reason": "not_seen_in_sync",
                    },
                )
        result.deactivated = len(orgs_to_deactivate)
        if orgs_to_deactivate:
            logger.info("Deactivated %d external orgs not seen in sync", len(orgs_to_deactivate))

    # Delete inactive orgs not linked to anything (leaf-first loop)
    if not dry_run:
        total_deleted = 0
        while True:
            orgs_to_delete = list(
                OrganizationUnit.objects.filter(end_date__lte=today)
                .exclude(assignment_relations__isnull=False)
                .exclude(children__isnull=False)
                .values_list("id", "tooi_identifier", "name")
            )
            if not orgs_to_delete:
                break
            for org_id, tooi, name in orgs_to_delete:
                create_event(
                    object_type="OrganizationUnit",
                    action="delete",
                    source="sync",
                    object_id=org_id,
                    context={
                        "tooi": tooi or "",
                        "name": name,
                        "reason": "inactive_and_unlinked",
                    },
                )
            OrganizationUnit.objects.filter(id__in=[org[0] for org in orgs_to_delete]).delete()
            total_deleted += len(orgs_to_delete)
        result.deleted = total_deleted
        if total_deleted:
            logger.info("Deleted %d inactive unlinked orgs", total_deleted)

    logger.info(
        "Sync completed: created=%s, updated=%s, unchanged=%s, deactivated=%s, deleted=%s",
        result.created,
        result.updated,
        result.unchanged,
        result.deactivated,
        result.deleted,
    )

    return result


def get_org_descendant_ids(root_ids: list[int]) -> set[int]:
    """Return the set of IDs for the given roots and all their descendants.

    Loads all OrganizationUnits once and traverses the tree in Python to avoid
    recursive SQL — fast for typical government org trees.
    """
    all_orgs = OrganizationUnit.objects.values_list("id", "parent_id")
    children_map: dict[int, list[int]] = {}
    for org_id, parent_id in all_orgs:
        if parent_id is not None:
            children_map.setdefault(parent_id, []).append(org_id)

    result: set[int] = set()
    queue = list(root_ids)
    while queue:
        current = queue.pop()
        result.add(current)
        queue.extend(children_map.get(current, []))
    return result


def org_counts_from_filtered(filtered_qs, model, org_lookup: str, group_field: str | None = None) -> Counter[int]:
    """Per-org counts from an already org-excluded, filter-applied queryset.

    Re-key on distinct row ids first: projecting the org id straight off a
    .distinct() queryset emits SELECT DISTINCT org_id and undercounts orgs
    shared by multiple rows. The base queryset already drops excluded orgs, so
    the exclusion is not re-applied here.

    With ``group_field`` the count is per distinct group (a colleague or an
    assignment) instead of per row, so it matches a list that shows one card
    per group.
    """
    rows = model.objects.filter(id__in=filtered_qs.values_list("id", flat=True))
    # Without group_field each row is its own group, so counting is per row.
    pairs = rows.values_list(org_lookup, group_field or "id").distinct()
    return Counter(oid for oid, _ in pairs if oid is not None)


def get_top_org_options(
    selected_org_ids: set[int],
    org_counts: Counter[int],
    *,
    selected_self_ids: set[int] | None = None,
    selected_type_labels: set[str] | None = None,
    selected_type_in: list[tuple[str, str]] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Turns per-org ``org_counts`` + the current selections into the opdrachtgever
    quick checkbox options, ordered by count then label.

    Each option carries its own ``param`` (``org``, ``org_self``, ``org_type`` or
    ``org_type_in``) so the sidebar quick row stays in sync with whatever was
    picked in the modal. The ``org`` group pads up to ``limit`` with the
    highest-count unselected orgs; self/type only appear when selected, having no
    top-N baseline. ``selected_type_in`` holds ``(ministry_public_id, type_name)``
    pairs; a pair whose ministry is unknown is left out.

    A selected option is always shown, appended below the top-N when it does not
    make the cut. The order never depends on selection — ticking an option
    jumping to the top felt jarring.
    """
    selected_self_ids = selected_self_ids or set()
    selected_type_labels = selected_type_labels or set()
    selected_type_in = selected_type_in or []

    selected_ids = set(selected_org_ids)
    self_ids = set(selected_self_ids)

    # The top-N is fixed on count regardless of selection, so ticking an option
    # never displaces a visible one.
    top_n = [oid for oid, _ in org_counts.most_common(limit)]
    org_wanted = selected_ids | set(top_n)

    options: list[dict] = []

    # Iterating the rows (not the wanted ids) keeps an id that no longer exists
    # out of the options instead of rendering it with a "None" value.
    if org_wanted:
        options.extend(
            {
                "param": "org",
                "value": str(public_id),
                "label": label or name,
                "count": org_counts.get(org_id, 0),
                "selected": org_id in selected_ids,
            }
            for org_id, label, name, public_id in OrganizationUnit.objects.filter(id__in=org_wanted).values_list(
                "id", "label", "name", "public_id"
            )
        )

    if self_ids:
        options.extend(
            {
                "param": "org_self",
                "value": str(public_id),
                "label": f"{label or name} (direct)",
                "count": org_counts.get(org_id, 0),
                "selected": True,
            }
            for org_id, label, name, public_id in OrganizationUnit.objects.filter(id__in=self_ids).values_list(
                "id", "label", "name", "public_id"
            )
        )

    options.extend(
        {
            "param": "org_type",
            "value": type_label,
            "label": ORG_TYPE_PLURAL.get(type_label, type_label),
            "count": 0,
            "selected": True,
        }
        for type_label in selected_type_labels
    )

    if selected_type_in:
        ministry_abbreviations = {
            str(public_id): ((abbreviations[0] if abbreviations else "") or label or name)
            for public_id, label, name, abbreviations in OrganizationUnit.objects.filter(
                public_id__in=parse_public_ids([pid for pid, _ in selected_type_in])
            ).values_list("public_id", "label", "name", "abbreviations")
        }
        options.extend(
            {
                "param": "org_type_in",
                "value": f"{ministry_public_id}:{type_name}",
                "label": nested_folder_label(ministry_abbreviations[ministry_public_id], type_name),
                "count": 0,
                "selected": True,
            }
            for ministry_public_id, type_name in selected_type_in
            if ministry_public_id in ministry_abbreviations
        )

    # Sorted on count then label, deliberately not on ``selected``: a just-ticked
    # option jumping to the top read as confusing.
    options.sort(key=lambda o: (-o["count"], o["label"]))
    return options


def build_org_hierarchy(org_self_counts: Counter[int], excluded_org_ids: list[int], *, prune_empty: bool) -> list[dict]:
    """Builds the grouped org tree hierarchy for the client modal."""
    all_orgs = list(
        OrganizationUnit.objects.exclude(id__in=excluded_org_ids).values(
            "id",
            "public_id",
            "parent_id",
            "name",
            "label",
            "abbreviations",
            "tooi_identifier",
            "related_ministry_tooi",
            "main_type__name",
        )
    )

    units_by_id: dict[int, dict] = {}
    for org in all_orgs:
        org["children_data"] = []
        org["self_count"] = org_self_counts.get(org["id"], 0)
        org["total_count"] = 0
        units_by_id[org["id"]] = org

    roots: list[dict] = []
    for unit in units_by_id.values():
        parent_id = unit["parent_id"]
        if parent_id and parent_id in units_by_id:
            units_by_id[parent_id]["children_data"].append(unit)
        else:
            roots.append(unit)

    # Each root's full (unordered) type set. Read before counting/pruning so we
    # can re-parent the nestable roots first. The set drives the "is this a
    # Ministerie?" check; main_type (loaded above with all_orgs) drives nesting.
    root_ids = {u["id"] for u in roots}
    type_links = OrganizationUnit.organization_types.through.objects.filter(
        organizationunit_id__in=root_ids
    ).values_list("organizationunit_id", "organizationtype__name")
    root_types: dict[int, set[str]] = {}
    for unit_id, type_name in type_links:
        root_types.setdefault(unit_id, set()).add(type_name)

    root_main_type: dict[int, str | None] = {unit["id"]: unit["main_type__name"] for unit in roots}

    # Presentation-only nesting: a root whose MAIN type is nestable and whose
    # related_ministry_tooi resolves to a ministry in the tree is moved under a
    # synthetic per-ministry type folder. The DB parent FK is untouched. Done
    # before compute_total/prune so counts roll up into the ministry naturally.
    ministry_by_tooi: dict[str, dict] = {}
    for unit in roots:
        if "Ministerie" in root_types.get(unit["id"], []) and unit["tooi_identifier"]:
            ministry_by_tooi[unit["tooi_identifier"]] = unit

    synthetic_folders: dict[tuple[int, str], dict] = {}
    nested_unit_ids: set[int] = set()
    for unit in roots:
        main_type = root_main_type.get(unit["id"])
        if main_type not in NESTED_ORG_TYPES:
            continue
        ministry = ministry_by_tooi.get(unit["related_ministry_tooi"])
        if ministry is None or ministry["id"] == unit["id"]:
            continue  # no resolvable ministry (or self) → keep at top level
        key = (ministry["id"], main_type)
        folder = synthetic_folders.get(key)
        if folder is None:
            # Label the folder with the ministry's abbreviation, same rule as the
            # chip (_org_chip_data): the abbreviation, else the label as fallback.
            ministry_abbreviation = (ministry["abbreviations"] or [None])[0] or ministry["label"] or ministry["name"]
            folder = {
                "id": f"group-{ministry['public_id']}-{main_type}",  # unique + ministry-scoped
                "type_label": main_type,
                "ministry_abbreviation": ministry_abbreviation,
                "synthetic_group": True,
                "self_count": 0,
                "total_count": 0,
                "children_data": [],
            }
            synthetic_folders[key] = folder
            ministry["children_data"].append(folder)
        folder["children_data"].append(unit)
        nested_unit_ids.add(unit["id"])

    roots = [r for r in roots if r["id"] not in nested_unit_ids]

    def compute_total(node: dict) -> int:
        total = node["self_count"]
        for child in node["children_data"]:
            total += compute_total(child)
        node["total_count"] = total
        return total

    for root in roots:
        compute_total(root)

    if prune_empty:

        def prune(node: dict) -> None:
            node["children_data"] = [c for c in node["children_data"] if c["total_count"] > 0]
            for child in node["children_data"]:
                prune(child)

        for root in roots:
            prune(root)
        roots = [r for r in roots if r["total_count"] > 0]

    def sort_key(node: dict) -> str:
        if node.get("synthetic_group"):
            return nested_folder_label(node["ministry_abbreviation"], node["type_label"])
        return node.get("label") or node.get("name") or ""

    def to_json(node: dict) -> dict:
        if node.get("synthetic_group"):
            return {
                "id": node["id"],
                "label": nested_folder_label(node["ministry_abbreviation"], node["type_label"]),
                "nr_of_placements": node["total_count"],
                "group": True,
                # A ministry-scoped folder; the assignment picker lets you tick
                # these (unlike the top-level type folders).
                "nested": True,
                "children": [to_json(c) for c in sorted(node["children_data"], key=sort_key)],
            }
        children_data = sorted(node["children_data"], key=sort_key)
        children_json = []
        has_children_with_placements = any(c["total_count"] > 0 for c in children_data)
        if node["self_count"] > 0 and has_children_with_placements:
            children_json.append(
                {
                    "id": f"self-{node['public_id']}",  # UUID -> str via f-string
                    "label": node["label"] or node["name"],
                    "abbreviations": node["abbreviations"] or [],
                    "self": True,
                    "nr_of_placements": node["self_count"],
                }
            )
        children_json.extend(to_json(child) for child in children_data)
        result: dict = {
            "id": str(node["public_id"]),
            "label": node["label"] or node["name"],
            "abbreviations": node["abbreviations"] or [],
            "nr_of_placements": node["total_count"],
        }
        if children_json:
            result["children"] = children_json
        return result

    # Top-level grouping for the remaining roots (nested units already removed).
    # A unit lands under its MAIN type only. Grouping a multi-type org under every
    # one of its types would emit the same node id in several folders, and the tree
    # keys nodes/rows by id — the duplicates then collapse and break checkbox sync.
    # One folder per unit mirrors the nested-folder rule.
    grouped: dict[str, list[dict]] = {}
    ungrouped: list[dict] = []
    for unit in roots:
        main_type = root_main_type.get(unit["id"])
        if main_type:
            grouped.setdefault(main_type, []).append(unit)
        else:
            ungrouped.append(unit)

    hierarchy = []
    for group_label in sorted(grouped.keys()):
        group_units = sorted(grouped[group_label], key=sort_key)
        total = sum(u["total_count"] for u in group_units)
        hierarchy.append(
            {
                "id": f"group-{group_label}",
                "label": ORG_TYPE_PLURAL.get(group_label, group_label),
                "nr_of_placements": total,
                "group": True,
                "children": [to_json(u) for u in group_units],
            }
        )
    hierarchy.extend(to_json(unit) for unit in sorted(ungrouped, key=sort_key))
    return hierarchy


def get_excluded_org_ids() -> set[int]:
    """Return IDs of organizations that should be hidden from display (e.g. intelligence services).

    Matches organizations by name or abbreviation against the exclusion lists,
    then includes all their descendants.
    """
    name_q = Q()
    for name in EXCLUDED_ORG_NAMES:
        name_q |= Q(name__icontains=name)
    abbr_q = Q()
    for abbr in EXCLUDED_ORG_ABBREVIATIONS:
        abbr_q |= Q(abbreviations__icontains=abbr)

    excluded_root_ids = list(OrganizationUnit.objects.filter(name_q | abbr_q).values_list("id", flat=True))
    if not excluded_root_ids:
        return set()
    return get_org_descendant_ids(excluded_root_ids)


_MIN_ABBREVIATION_SEARCH_LENGTH = 2
_MAX_ABBREVIATION_RESULTS = 5


def find_orgs_by_abbreviation(search_term: str) -> list[dict]:
    """Find active orgs where an abbreviation exactly matches the search term (case-insensitive).

    Uses icontains as a fast pre-filter, then checks for exact element match in Python.
    """
    term = search_term.strip()
    if len(term) < _MIN_ABBREVIATION_SEARCH_LENGTH:
        return []
    excluded_ids = get_excluded_org_ids()
    qs = OrganizationUnit.objects.filter(
        abbreviations__icontains=term,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gt=timezone.now().date()))
    if excluded_ids:
        qs = qs.exclude(id__in=excluded_ids)
    term_lower = term.lower()
    results = []
    for org in qs.values("id", "public_id", "label", "name", "abbreviations"):
        if any(abbr.lower() == term_lower for abbr in (org["abbreviations"] or [])):
            results.append({"public_id": org["public_id"], "label": org["label"], "name": org["name"]})
            if len(results) >= _MAX_ABBREVIATION_RESULTS:
                break
    return results


def resolve_related_ministry(org: OrganizationUnit) -> OrganizationUnit | None:
    """The ministry a root org nests under, via ``related_ministry_tooi``.

    Only for roots whose main type is nestable (mirrors the picker's nesting in
    ``build_org_hierarchy``); returns ``None`` otherwise, so a normal org keeps
    its plain parent-chain breadcrumb. Also ``None`` when the tooi resolves to no
    org (e.g. an excluded/unsynced ministry) — a graceful, unchanged breadcrumb.
    """
    if org.parent_id or not org.related_ministry_tooi:
        return None
    if org.main_type is None or org.main_type.name not in NESTED_ORG_TYPES:
        return None
    return OrganizationUnit.objects.filter(tooi_identifier=org.related_ministry_tooi).exclude(id=org.id).first()


def get_ministry_nested_root_ids(ministry_toois: list[str], *, type_name: str | None = None) -> list[int]:
    """Root org ids that nest under the given ministries in the picker (boom).

    Same rule as ``build_org_hierarchy`` and ``resolve_related_ministry``: an org
    nests under a ministry only when it is a DB root (no parent), its ``main_type``
    (the overheid.nl breadcrumb category) is in ``NESTED_ORG_TYPES``, and its
    ``related_ministry_tooi`` points at one of the given ministries. Pass
    ``type_name`` to restrict to a single nestable type (the ``org_type_in``
    facet); it is ignored when not itself nestable.

    Callers wrap the result in ``get_org_descendant_ids`` to include subtrees.
    Keying on the MAIN type (not any attached type) is what keeps orgs merely
    linked via ``related_ministry_tooi`` — e.g. a stichting — out of the results.
    """
    if not ministry_toois:
        return []
    allowed_types = NESTED_ORG_TYPES if type_name is None else (NESTED_ORG_TYPES & {type_name})
    if not allowed_types:
        return []
    return list(
        OrganizationUnit.objects.filter(
            parent__isnull=True,
            related_ministry_tooi__in=ministry_toois,
            main_type__name__in=allowed_types,
        ).values_list("id", flat=True)
    )


def get_type_folder_root_ids(type_names: list[str]) -> list[int]:
    """Root org ids in the picker's top-level type folders for ``type_names``.

    Same rule as ``build_org_hierarchy``: a DB root is filed under its MAIN type
    only, and a root that nests under its ministry has left the top-level folder.
    The roots nested under a ministry in the folder are included instead, so the
    "Ministeries" folder matches the ministries plus what the picker shows under
    them. Callers wrap the result in ``get_org_descendant_ids`` for subtrees.
    """
    if not type_names:
        return []
    ministry_toois = set(
        OrganizationUnit.objects.filter(parent__isnull=True, organization_types__name="Ministerie")
        .exclude(tooi_identifier__isnull=True)
        .exclude(tooi_identifier="")
        .values_list("tooi_identifier", flat=True)
    )
    roots = OrganizationUnit.objects.filter(parent__isnull=True, main_type__name__in=type_names)
    nested = Q(main_type__name__in=NESTED_ORG_TYPES, related_ministry_tooi__in=ministry_toois)
    folder_roots = list(roots.exclude(nested).values_list("id", "tooi_identifier"))
    folder_ministry_toois = [tooi for _, tooi in folder_roots if tooi in ministry_toois]
    return [root_id for root_id, _ in folder_roots] + get_ministry_nested_root_ids(folder_ministry_toois)


def get_org_breadcrumb(org: OrganizationUnit, base_url: str = "/") -> dict:
    """Build breadcrumb data for an organization: label + clickable ancestor path."""
    ancestors = []
    root = org
    current = org.parent
    while current:
        label = current.abbreviation or current.label or current.name
        ancestors.append({"label": label, "url": f"{base_url}?org={current.public_id}"})
        root = current  # the last ancestor reached is the chain root
        current = current.parent
    ancestors.reverse()

    # The ministry link lives on the ROOT of the chain (e.g. RVB), not the leaf
    # (Atelier Rijksbouwmeester). Resolve from the root so a descendant of a
    # nestable root also shows the ministry the picker nests that root under.
    ministry = resolve_related_ministry(root)
    if ministry is not None:
        ancestors.insert(
            0,
            {
                "label": ministry.abbreviation or ministry.label or ministry.name,
                "url": f"{base_url}?org={ministry.public_id}",
            },
        )

    is_self = org.children.filter(assignment_relations__isnull=False).exists()
    label = org.label or org.name
    url = f"{base_url}?org_self={org.public_id}" if is_self else f"{base_url}?org={org.public_id}"

    return {"label": label, "url": url, "ancestors": ancestors}


def get_org_levels_action(org: OrganizationUnit, base_url: str = "/") -> dict:
    """Build the "Bekijk opdrachten" row action for one organization.

    One submenu entry per hierarchy step, from the organization up to the root:
    the node itself filters narrowly, a higher level broadly. Filtering only on
    the lowest node would hit the unit sharing the fewest other assignments.
    """
    breadcrumb = get_org_breadcrumb(org, base_url)
    levels = [
        {"text": level["label"], "icon": "stack", "attrs": f'data-href="{level["url"]}"'}
        for level in [breadcrumb, *reversed(breadcrumb["ancestors"])]
    ]
    return {"text": "Bekijk opdrachten", "icon": "stack", "submenu": levels}
