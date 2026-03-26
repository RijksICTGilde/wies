from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

SERVICE_STATUS = {
    "CONCEPT": "Concept",
    "OPEN": "Open",
    "GESLOTEN": "Gesloten",
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
    organizations = models.ManyToManyField(
        "OrganizationUnit",
        through="AssignmentOrganizationUnit",
        related_name="assignments",
        verbose_name="Organisatie-eenheden",
    )
    owner = models.ForeignKey("Colleague", models.SET_NULL, null=True, blank=False, related_name="owned_assignments")
    extra_info = models.TextField(blank=True, max_length=5000)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

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
    status = models.CharField(max_length=20, choices=SERVICE_STATUS, default="OPEN")
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


class OrganizationType(models.Model):
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.label} ({self.name})"


class OrganizationUnit(models.Model):
    """Hierarchical organization model for Dutch government organizations."""

    # === Basic fields ===
    name = models.CharField(max_length=200, verbose_name="Naam")
    label = models.CharField(max_length=200, blank=True)
    abbreviations = models.JSONField(  # first in list is main abbreviation
        default=list,
        blank=True,
        verbose_name="Afkortingen",
        help_text='Lijst van afkortingen, bijv. ["BZK", "MinBZK"]',
    )
    organization_types = models.ManyToManyField("OrganizationType", blank=True)
    related_ministry_tooi = models.CharField(
        max_length=200,
        default="",
        validators=[
            RegexValidator(
                regex=r"^https://identifier\.overheid\.nl/tooi/",
                message="TOOI identifier moet een URI zijn (https://identifier.overheid.nl/tooi/...)",
            )
        ],
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Bovenliggende organisatie",
    )

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
    system_id = models.CharField(
        max_length=20,
        default="",
        help_text=("SysteemId - gebruikt op organisatie.overheid.nl voor resources"),
    )
    # Source URL: link to organisaties.overheid.nl page
    source_url = models.URLField(
        default="",
        verbose_name="Bronpagina",
        help_text=(
            "URL naar de pagina op organisaties.overheid.nl. "
            "Als deze is gevuld, komt de organisatie uit een externe bron "
            "en zijn de gegevens niet bewerkbaar."
        ),
    )

    # === Status ===
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Einddatum",
        help_text="Datum waarop de organisatie is opgeheven.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisatie-eenheid"
        verbose_name_plural = "Organisatie-eenheden"
        indexes = [
            models.Index(fields=["parent"]),
            models.Index(fields=["end_date"]),
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


class OrganizationUnitRole(models.TextChoices):
    """Role of an organization unit in relation to an assignment."""

    PRIMARY = "PRIMARY", "Primaire opdrachtgever"
    INVOLVED = "INVOLVED", "Betrokken partij"


class AssignmentOrganizationUnit(models.Model):
    """Through table between Assignment and OrganizationUnit with role.

    Each assignment can have multiple organization units with different roles:
    - PRIMARY: The main client responsible for the assignment (max 1 per assignment)
    - INVOLVED: Other organizations involved in the assignment
    """

    assignment = models.ForeignKey("Assignment", on_delete=models.CASCADE, related_name="organization_relations")
    organization = models.ForeignKey("OrganizationUnit", on_delete=models.PROTECT, related_name="assignment_relations")
    role = models.CharField(
        max_length=20,
        choices=OrganizationUnitRole,
        default=OrganizationUnitRole.PRIMARY,
        verbose_name="Rol",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment"],
                condition=models.Q(role="PRIMARY"),
                name="unique_primary_per_assignment",
            )
        ]

    def __str__(self):
        return f"{self.assignment.name} - {self.organization.name}"


TASK_STATUS = {
    "pending": "Pending",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
}


class Task(models.Model):
    """Model for tracking long-running background tasks."""

    command = models.CharField(max_length=100, db_index=True, help_text="Management command name to execute")
    status = models.CharField(max_length=20, choices=TASK_STATUS, default="pending", db_index=True)
    parameters = models.JSONField(default=dict, blank=True, help_text="Parameters to pass to the command")
    result = models.JSONField(null=True, blank=True, help_text="Result data from the command execution")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="tasks")
    timeout_minutes = models.IntegerField(help_text="Task timeout in minutes")
    error_message = models.TextField(blank=True, help_text="Error message if task failed")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.command} ({self.status}) - {self.created_at}"

    def is_expired(self) -> bool:
        """Check if a running task has exceeded its timeout."""
        if self.status != "running" or not self.started_at:
            return False
        timeout_delta = timezone.timedelta(minutes=self.timeout_minutes)
        return timezone.now() > self.started_at + timeout_delta
