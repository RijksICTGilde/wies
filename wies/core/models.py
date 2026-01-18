from django.contrib.auth.models import AbstractUser
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


class Ministry(models.Model):
    name = models.CharField(max_length=98)
    abbreviation = models.CharField(max_length=10)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "ministries"

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


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
    organization = models.CharField(blank=True)
    ministry = models.ForeignKey("Ministry", models.SET_NULL, null=True, blank=False)
    owner = models.ForeignKey("Colleague", models.SET_NULL, null=True, blank=False, related_name="owned_assignments")
    extra_info = models.TextField(blank=True, max_length=5000)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(blank=True)

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
    PERIOD_SOURCE_CHOICES = {
        SERVICE: "Neem over van dienst",
        PLACEMENT: "Specifiek voor inzet",
    }

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
    PERIOD_SOURCE_CHOICES = {
        ASSIGNMENT: "Neem over van opdracht",
        SERVICE: "Specifiek voor dienst",
    }

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
        return self.description

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
    # deliberately no foreignkey, because of cascading/nulling. this should be append-only.
    # could no longer exist. empty string used for system creation
    user_email = models.EmailField(max_length=255, blank=True, db_index=True)
    name = models.CharField(max_length=32, db_index=True)
    context = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} - {self.user_email}"
