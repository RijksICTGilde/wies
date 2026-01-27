from typing import override

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

ASSIGNMENT_STATUS = {
    "VACATURE": "VACATURE",
    "INGEVULD": "INGEVULD",
}

SOURCE_CHOICES = {
    "otys_iir": "OTYS IIR",
    "wies": "Wies",
}


DEFAULT_LABELS = {
    "Merk": {
        "color": "#DCE3EA",
        "labels": {
            "Rijksconsultants",
            "I-Interim Rijk",
            "Rijks ICT Gilde",
            "Rijks I-Traineeship",
            "Innoveren met Impact",
            "RADIO",
            "Leer en ontwikkel campus",
            "Intercoach",
            "Mindful Rijk",
            "Gateway review",
            "Delta review",
        },
    },
    "Expertise": {
        "color": "#B3D7EE",
        "labels": {
            "Strategie, beleid, governance en compliance",
            "Architectuur en technologie",
            "Agile, project- programma- en portfoliomanagement",
            "Proces- en ketenmanagement",
            "Verander- en transformatiemanagement",
            "Interimmanagement en advies",
            "AI",
            "ICT",
            "Software en data engineering",
            "Cloud en platform technologie",
            "Security en privacy",
            "Opleiding, training en ontwikkeling",
            "Kennis- en innovatiemanagement",
        },
    },
    "Thema": {
        "color": "#FFE9B8",
        "labels": {
            "Digitale weerbaarheid",
            "Artificiële intelligentie",
            "Netwerksamenwerking",
            "Ambtelijk en digitaal vakmanschap",
            "Innovatieve en lerende overheid",
        },
    },
}


class LabelCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7)  # Hex color like #FF5733

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Label(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey("LabelCategory", models.CASCADE, related_name="labels")

    class Meta:
        ordering = [Lower("name")]
        unique_together = [["name", "category"]]

    def __str__(self):
        return f"{self.name}"


# Organization type configuration: single source of truth for type metadata
# - label: Dutch UI label
# - is_root: True if this type must be root (no parent allowed), False if parent required
# - xml_name: Value in <classificatie> element of organisaties.overheid.nl XML export
#             (https://organisaties.overheid.nl/archive/exportOO.xml)
#             None = not importable from XML (internal hierarchy types)
# - valid_parents: List of allowed parent types (only for is_root=False types)
#                  Default is None = any parent allowed
ORGANIZATION_TYPE_CONFIG = {
    # === Root types (can exist without parent) ===
    # Government layers
    "ministerie": {"label": "Ministerie", "is_root": True, "xml_name": "Ministerie"},
    "gemeente": {"label": "Gemeente", "is_root": True, "xml_name": "Gemeente"},
    "provincie": {"label": "Provincie", "is_root": True, "xml_name": "Provincie"},
    "waterschap": {"label": "Waterschap", "is_root": True, "xml_name": "Waterschap"},
    # === Sub types (require parent) ===
    # Ministry hierarchy
    "directoraat_generaal": {
        "label": "Directoraat-Generaal",
        "is_root": False,
        "xml_name": None,
        "valid_parents": ["ministerie"],
    },
    "directie": {
        "label": "Directie",
        "is_root": False,
        "xml_name": None,
        "valid_parents": ["directoraat_generaal", "ministerie", "agentschap", "gemeente", "provincie", "waterschap"],
    },
    "afdeling": {
        "label": "Afdeling",
        "is_root": False,
        "xml_name": None,
        "valid_parents": ["directie", "directoraat_generaal", "agentschap", "gemeente", "provincie"],
    },
    "organisatieonderdeel": {
        "label": "Organisatieonderdeel",
        "is_root": False,
        "xml_name": "Organisatieonderdeel",
        "valid_parents": [
            "ministerie",
            "gemeente",
            "provincie",
            "waterschap",
            "directoraat_generaal",
            "directie",
            "afdeling",
            "agentschap",
            "zelfstandig_bestuursorgaan",
            "rechtspersoon_wettelijke_taak",
            "stichting",
            "staatsdeelneming",
            "hoog_college_van_staat",
            "rechtspraak",
            "politie",
            "kabinet_van_de_koning",
            "publiekrechtelijke_instelling",
            "speciaal_sectorbedrijf",
            "gemeenschappelijke_regeling",
            "caribisch_openbaar_lichaam",
            "shared_service_organisatie",
            "planbureau",
            "adviescollege",
            "inspectie",
        ],
    },
    # === More root types that can exist without parent ===
    # Independent bodies (top-level)
    "zelfstandig_bestuursorgaan": {
        "label": "Zelfstandig Bestuursorgaan",
        "is_root": True,
        "xml_name": "Zelfstandig bestuursorgaan",
    },
    "rechtspersoon_wettelijke_taak": {
        "label": "Rechtspersoon met Wettelijke Taak",
        "is_root": True,
        "xml_name": None,
    },
    "stichting": {"label": "Stichting", "is_root": True, "xml_name": None},
    "staatsdeelneming": {"label": "Staatsdeelneming", "is_root": True, "xml_name": None},
    # State institutions
    "hoog_college_van_staat": {
        "label": "Hoog College van Staat",
        "is_root": True,
        "xml_name": "Hoog College van Staat",
    },
    "rechtspraak": {"label": "Rechtspraak", "is_root": True, "xml_name": "Rechtspraak"},
    "politie": {"label": "Politie", "is_root": True, "xml_name": "Politie en brandweer"},
    "kabinet_van_de_koning": {
        "label": "Kabinet van de Koning",
        "is_root": True,
        "xml_name": "Kabinet van de Koning",
    },
    # Other top-level
    "publiekrechtelijke_instelling": {
        "label": "Publiekrechtelijke Instelling",
        "is_root": True,
        "xml_name": None,
    },
    "speciaal_sectorbedrijf": {
        "label": "Speciaal Sectorbedrijf",
        "is_root": True,
        "xml_name": None,
    },
    "gemeenschappelijke_regeling": {
        "label": "Gemeenschappelijke Regeling",
        "is_root": True,
        "xml_name": "Gemeenschappelijke regeling",
    },
    "caribisch_openbaar_lichaam": {
        "label": "Caribisch Openbaar Lichaam",
        "is_root": True,
        "xml_name": "Caribisch openbaar lichaam",
    },
    # === More sub types that require parent ===
    # Execution & independent units (under ministry)
    "agentschap": {
        "label": "Agentschap",
        "is_root": False,
        "xml_name": "Agentschap",
        "valid_parents": ["ministerie"],
    },
    "shared_service_organisatie": {
        "label": "Shared Service Organisatie",
        "is_root": False,
        "xml_name": None,
        "valid_parents": ["ministerie"],
    },
    "planbureau": {
        "label": "Planbureau",
        "is_root": False,
        "xml_name": None,
        "valid_parents": ["ministerie"],
    },
    "adviescollege": {
        "label": "Adviescollege",
        "is_root": False,
        "xml_name": "Adviescollege",
        "valid_parents": ["ministerie", "directoraat_generaal"],
    },
    "inspectie": {
        "label": "Inspectie",
        "is_root": False,
        "xml_name": None,
        "valid_parents": ["ministerie", "directoraat_generaal"],
    },
}

OrganizationType = models.TextChoices(
    "OrganizationType",
    {key.upper(): (key, config["label"]) for key, config in ORGANIZATION_TYPE_CONFIG.items()},
)


ROOT_ORGANIZATION_TYPES = [type_key for type_key, config in ORGANIZATION_TYPE_CONFIG.items() if config["is_root"]]


# Derived from ORGANIZATION_TYPE_CONFIG: mapping from XML classificatie to our type
# Used by sync_organizations management command to import from organisaties.overheid.nl
# Keys are the exact strings used in the XML <classificatie> element
XML_TYPE_MAPPING = {
    config["xml_name"]: type_key
    for type_key, config in ORGANIZATION_TYPE_CONFIG.items()
    if config["xml_name"] is not None
}


class OrganizationUnitQuerySet(models.QuerySet):
    """QuerySet for Organization model with tree operations."""

    def active(self):
        """Filter to only active organizations."""
        return self.filter(is_active=True)

    def roots(self):
        return self.filter(parent__isnull=True)

    def of_type(self, *org_types):
        return self.filter(organization_type__in=org_types)

    def with_descendants(self, root_ids: list[int]) -> list[int]:
        """Get all organization IDs that fall under root_ids (including roots)."""
        all_ids = set(root_ids)
        current_level = list(root_ids)
        while current_level:
            children = list(self.filter(parent_id__in=current_level).values_list("id", flat=True))
            current_level = children
            all_ids.update(children)
        return list(all_ids)


class OrganizationUnitManager(models.Manager.from_queryset(OrganizationUnitQuerySet)):
    """Manager filtering non-deleted records by default."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def with_deleted(self):
        """Include all records, including deleted."""
        return super().get_queryset()


class OrganizationUnit(models.Model):
    """Hierarchical organization model for Dutch government organizations."""

    # === Basic fields ===
    name = models.CharField(max_length=200, verbose_name="Naam")
    abbreviations = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Afkortingen",
        help_text='Lijst van afkortingen, bijv. ["BZK", "MinBZK"]',
    )
    organization_type = models.CharField(
        max_length=30,
        choices=OrganizationType.choices,
        verbose_name="Type organisatie",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Bovenliggende organisatie",
    )
    is_active = models.BooleanField(default=True, verbose_name="Actief")

    # === External identifiers ===
    # TOOI: primary identifier for sync with organisaties.overheid.nl
    tooi_identifier = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^https://identifier\.overheid\.nl/tooi/",
                message="TOOI identifier moet een URI zijn (https://identifier.overheid.nl/tooi/...)",
            )
        ],
        verbose_name="TOOI-identifier",
        help_text=(
            "Unieke URI uit organisaties.overheid.nl (bijv. "
            "'https://identifier.overheid.nl/tooi/id/oorg/oorg10264'). "
            "Zie: https://standaarden.overheid.nl/tooi/"
        ),
    )
    # OIN: optional, for PKIoverheid digital authentication
    oin_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        validators=[RegexValidator(regex=r"^\d{20}$", message="OIN moet exact 20 cijfers zijn")],
        verbose_name="OIN-nummer",
        help_text=(
            "Organisatie Identificatienummer - uniek 20-cijferig nummer uit het "
            "Logius OIN-register. Wordt gebruikt voor digitale communicatie (PKIoverheid). "
            "Niet verplicht. Zie: https://oinregister.logius.nl"
        ),
    )
    # Source URL: link to organisaties.overheid.nl page
    source_url = models.URLField(
        blank=True,
        default="",
        verbose_name="Bronpagina",
        help_text=(
            "URL naar de pagina op organisaties.overheid.nl. "
            "Als deze is gevuld, komt de organisatie uit een externe bron "
            "en zijn de gegevens niet bewerkbaar."
        ),
    )

    # === History tracking ===
    previous_names = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Vorige namen",
        help_text='[{"name": "Digitale Overheid", "until": "2024-01-01"}]',
    )

    # === Successor relation (for mergers/reorganizations) ===
    # is_active=False + successor = merged into another org
    # is_active=False + no successor = dissolved without successor
    successor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predecessors",
        verbose_name="Opvolger",
        help_text="Organisatie die deze heeft overgenomen (bij fusie/opheffing)",
    )

    # === Soft delete ===
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Verwijderd op",
        help_text="Tijdstip van soft delete. Null = niet verwijderd.",
    )

    objects = OrganizationUnitManager()

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisatie-eenheid"
        verbose_name_plural = "Organisatie-eenheden"
        indexes = [
            models.Index(fields=["parent", "is_active"]),
        ]

    def __str__(self):
        if self.abbreviation:
            return f"{self.name} ({self.abbreviation})"
        return self.name

    @property
    def abbreviation(self) -> str:
        """Return the first abbreviation, or empty string if none."""
        if self.abbreviations and len(self.abbreviations) > 0:
            return self.abbreviations[0]
        return ""

    def clean(self):
        """Validate model constraints."""
        # Root types cannot have a parent
        if self.parent and self.organization_type in ROOT_ORGANIZATION_TYPES:
            msg = f"{self.get_organization_type_display()} mag geen bovenliggende organisatie hebben."
            raise ValidationError(msg)

        # Prevent circular references
        if self.pk and self.parent:
            seen = set()
            current = self.parent
            while current:
                if current.pk == self.pk:
                    msg = "Circulaire referentie: organisatie kan niet zijn eigen voorouder zijn."
                    raise ValidationError(msg)
                if current.pk in seen:
                    break
                seen.add(current.pk)
                current = current.parent

        # Validate hierarchy based on type configuration
        type_config = ORGANIZATION_TYPE_CONFIG.get(self.organization_type, {})

        if self.parent:
            # Root types cannot have a parent
            if type_config.get("is_root"):
                msg = f"{self.get_organization_type_display()} mag geen bovenliggende organisatie hebben."
                raise ValidationError(msg)

            # Check allowed parent types
            valid_parents = type_config.get("valid_parents")
            if valid_parents is not None and self.parent.organization_type not in valid_parents:
                msg = (
                    f"{self.get_organization_type_display()} kan niet onder "
                    f"{self.parent.get_organization_type_display()} vallen."
                )
                raise ValidationError(msg)

    def get_ancestors(self):
        """Return all ancestor organizations (generator)."""
        current = self.parent
        while current:
            yield current
            current = current.parent

    def get_root(self):
        """Return the ministry/root of this organization."""
        ancestors = list(self.get_ancestors())
        return ancestors[-1] if ancestors else self

    def get_descendants(self):
        """Return all descendant organizations (recursive)."""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_full_path(self) -> str:
        """Return full path as breadcrumb string: 'BZK > DGDOO > Directie XYZ'."""
        ancestors = list(self.get_ancestors())
        ancestors.reverse()
        ancestors.append(self)
        return " > ".join(org.abbreviation or org.name for org in ancestors)

    def dissolve(self, successor=None):
        """Mark organization as dissolved, optionally with successor."""
        self.is_active = False
        if successor:
            self.successor = successor
        self.save(update_fields=["is_active", "successor"])

    @property
    def is_from_external_source(self) -> bool:
        """True if this organization was synced from an external source."""
        return bool(self.source_url)

    @property
    def has_predecessors(self) -> bool:
        """True if this organization has predecessors (e.g., after merger)."""
        return self.predecessors.exists()

    @property
    def has_successor(self) -> bool:
        """True if this organization has a successor (has been dissolved)."""
        return self.successor is not None

    def get_predecessors(self):
        """Return all direct predecessors."""
        return self.predecessors.all()

    def get_all_predecessors(self):
        """Return all predecessors recursively (full history)."""
        all_predecessors = []
        for pred in self.predecessors.all():
            all_predecessors.append(pred)
            all_predecessors.extend(pred.get_all_predecessors())
        return all_predecessors

    def get_successor_chain(self):
        """Return chain of successors up to current active organization."""
        chain = []
        current = self.successor
        while current:
            chain.append(current)
            current = current.successor
        return chain

    def get_current_successor(self):
        """Return the current active successor (end of chain)."""
        if not self.successor:
            return None
        chain = self.get_successor_chain()
        return chain[-1] if chain else None

    @override
    def delete(self, *args, **kwargs):
        """Soft delete instead of hard delete. Prevents deletion of TOOI-synced orgs."""
        if self.tooi_identifier:
            msg = "Organisaties met TOOI-identifier kunnen niet worden verwijderd."
            raise models.ProtectedError(msg, [self])
        if self.children.exists():
            msg = "Organisaties met onderliggende eenheden kunnen niet worden verwijderd."
            raise models.ProtectedError(msg, [self])
        if self.assignment_relations.exists():
            msg = "Organisaties met gekoppelde opdrachten kunnen niet worden verwijderd."
            raise models.ProtectedError(msg, [self])

        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, *args, **kwargs):
        """Actually delete from database. Use with caution."""
        super().delete(*args, **kwargs)

    def restore(self):
        """Restore a soft-deleted organization."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def rename(self, new_name: str) -> None:
        """Rename organization and preserve old name in history."""
        today = timezone.now().date().isoformat()
        history_entry = {"name": self.name, "until": today}
        self.previous_names.append(history_entry)
        self.name = new_name
        self.save(update_fields=["name", "previous_names"])


class OrganizationUnitRole(models.TextChoices):
    """Role of an organization unit in relation to an assignment."""

    PRIMARY = "PRIMARY", "Primaire organisatie"
    INVOLVED = "INVOLVED", "Betrokken partij"
    SUCCESSOR = "SUCCESSOR", "Opvolger (na overdracht)"


class AssignmentOrganizationUnit(models.Model):
    """Through table between Assignment and OrganizationUnit with role and period.

    Each assignment can have multiple organization units with different roles:
    - PRIMARY: The main organization responsible for the assignment (max 1 per assignment)
    - INVOLVED: Other organizations involved in the assignment
    - SUCCESSOR: Organization that took over after transfer (with effective dates)
    """

    assignment = models.ForeignKey("Assignment", on_delete=models.CASCADE, related_name="organization_relations")
    organization = models.ForeignKey("OrganizationUnit", on_delete=models.PROTECT, related_name="assignment_relations")
    role = models.CharField(
        max_length=20,
        choices=OrganizationUnitRole,
        default=OrganizationUnitRole.PRIMARY,
        verbose_name="Rol",
    )
    effective_from = models.DateField(null=True, blank=True, verbose_name="Geldig vanaf")
    effective_until = models.DateField(null=True, blank=True, verbose_name="Geldig tot")

    class Meta:
        verbose_name = "Opdracht-organisatie koppeling"
        verbose_name_plural = "Opdracht-organisatie koppelingen"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "organization", "role"],
                name="unique_assignment_org_role",
            ),
            # Ensure only one PRIMARY organization per assignment
            models.UniqueConstraint(
                fields=["assignment"],
                condition=models.Q(role="PRIMARY"),
                name="unique_primary_org_per_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.assignment.name} - {self.organization.name} ({self.get_role_display()})"


class Skill(models.Model):
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    email = models.EmailField(unique=True)
    labels = models.ManyToManyField("Label", related_name="users", blank=True)


class Colleague(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="colleague")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    skills = models.ManyToManyField("Skill", blank=True)
    labels = models.ManyToManyField("Label", related_name="colleagues", blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(blank=True)
    # placements via reversed relation

    def __str__(self):
        return self.name


# Create your models here.
class Assignment(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(null=True, blank=True)
    # placements through foreignkey on Placement
    # services through foreignkey on Service
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default="LEAD")
    owner = models.ForeignKey("Colleague", models.SET_NULL, null=True, blank=False, related_name="owned_assignments")
    extra_info = models.TextField(blank=True, max_length=5000)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(blank=True)

    # New: M2M via through model for organization hierarchy
    organizations = models.ManyToManyField(
        "OrganizationUnit",
        through="AssignmentOrganizationUnit",
        related_name="assignments",
        verbose_name="Organisatie-eenheden",
    )

    def __str__(self):
        return self.name

    @property
    def phase(self):
        today_date = timezone.now().date()
        if None in (self.start_date, self.end_date):
            # this is undertermined
            return None
        if self.start_date > today_date:
            return "planned"
        if self.end_date < today_date:
            return "completed"
        return "active"

    def get_primary_organization(self):
        """Return the primary organization (or None)."""
        rel = (
            self.organization_relations.filter(role=OrganizationUnitRole.PRIMARY).select_related("organization").first()
        )
        return rel.organization if rel else None


class Placement(models.Model):
    SERVICE = "SERVICE"
    PLACEMENT = "PLACEMENT"
    PERIOD_SOURCE_CHOICES = {SERVICE: "Neem over van dienst", PLACEMENT: "Specifiek voor inzet"}

    colleague = models.ForeignKey(
        "Colleague", models.CASCADE, related_name="placements"
    )  # if we implement anonymization, this should maybe be changed
    service = models.ForeignKey("Service", models.CASCADE, related_name="placements")
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=SERVICE)
    specific_start_date = models.DateField(null=True, blank=True)  # do not use, use properties below
    specific_end_date = models.DateField(null=True, blank=True)  # do not use, use properties below
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(blank=True)  # only for non wies

    def __str__(self):
        return f"{self.colleague.name} - {self.service.description}"

    @property
    def start_date(self):
        """
        This property has N+1 query issues.
        Use `core.querysets.annotate_placement_dates` instead for batch operations.
        """
        if self.period_source == "SERVICE":
            return self.service.start_date
        return self.specific_start_date

    @property
    def end_date(self):
        """
        This property has N+1 query issues.
        Use `core.querysets.annotate_placement_dates` instead for batch operations.
        """
        if self.period_source == "SERVICE":
            return self.service.end_date
        return self.specific_end_date


class Service(models.Model):
    ASSIGNMENT = "ASSIGNMENT"
    SERVICE = "SERVICE"
    PERIOD_SOURCE_CHOICES = {ASSIGNMENT: "Neem over van opdracht", SERVICE: "Specifiek voor dienst"}

    assignment = models.ForeignKey("Assignment", models.CASCADE, related_name="services")
    description = models.CharField(max_length=500)
    skill = models.ForeignKey("Skill", models.SET_NULL, related_name="services", null=True, blank=True)
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=ASSIGNMENT)
    specific_start_date = models.DateField(null=True, blank=True)  # do not use directly, see property below
    specific_end_date = models.DateField(null=True, blank=True)  # do not use directly, see property below
    # placements via reverse relation
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(blank=True)  # only for non wies

    def __str__(self):
        return f"{self.description}"

    @property
    def start_date(self):
        """
        This does not scale well on batch operations
        consider a dedicated function similar to `core.querysets.annotate_placement_dates`
        """
        if self.period_source == "ASSIGNMENT":
            return self.assignment.start_date
        return self.specific_start_date

    @property
    def end_date(self):
        """
        This does not scale well on batch operations
        consider a dedicated function similar to `core.querysets.annotate_placement_dates`
        """
        if self.period_source == "ASSIGNMENT":
            return self.assignment.end_date
        return self.specific_end_date


class Event(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # deliberately no foreignkey, because of cascading/nulling.
    # this should be append-only. could no longer exist. empty string used for system creation
    user_email = models.EmailField(max_length=255, blank=True, db_index=True)
    name = models.CharField(max_length=32, db_index=True)
    context = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} ({self.user_email})"
