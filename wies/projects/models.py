from django.db import models
from django.urls import reverse
from django.db.models import Max


ASSIGNMENT_STATUS = {
    'LEAD': "LEAD",
    'OPEN': "OPEN",
    'LOPEND': "LOPEND",
    'AFGEWEZEN': "AFGEWEZEN",
    'HISTORISCH': "HISTORISCH",
}

ASSIGNMENT_TYPE = {
    'GROUP': "GROUP",
    'INDIVIDUAL': "INDIVIDUAL",
}


class Skill(models.Model):
    name = models.CharField(max_length=30, unique=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Colleague(models.Model):
    name = models.CharField(max_length=200)
    skills = models.ManyToManyField('Skill', blank=True)
    # placements via reversed relation

    @property
    def end_date(self):
        return self.placements.aggregate(Max('end_date'))['end_date__max']

    def get_absolute_url(self):
        return reverse("colleague-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

# Create your models here.
class Assignment(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)  #TODO: timezone aware?
    end_date = models.DateField(null=True, blank=True)  #TODO: timezone aware?
    # placements through foreignkey on Placement
    # services through foreignkey on Service
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='LEAD')
    organization = models.CharField(blank=True)
    extra_info = models.TextField(blank=True)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE, default='GROUP')

    def get_total_services_cost(self):
        """Calculate total cost of all services in this assignment"""
        total = 0
        for service in self.services.all():
            if service.cost_type == "FIXED_PRICE" and service.fixed_cost:
                total += service.fixed_cost
            elif service.cost_type == "PER_HOUR":
                service_cost = service.get_total_cost()
                if service_cost:
                    total += service_cost
        return total

    def get_absolute_url(self):
        return reverse("assignment-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Placement(models.Model):
    SERVICE = "SERVICE"
    PLACEMENT = "PLACEMENT"
    PERIOD_SOURCE_CHOICES = {
        SERVICE: "Neem over van dienst",
        PLACEMENT: "Specifiek voor inzet"
    }
    
    colleague = models.ForeignKey('Colleague', models.CASCADE, related_name='placements', null=True, blank=True) # TODO: removal of colleague triggers removal of placement, probably undesirable
    service = models.ForeignKey('Service', models.CASCADE, related_name='placements')
    hours_per_week = models.IntegerField(null=True, blank=True)
    skills = models.ManyToManyField('Skill', blank=True)
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=SERVICE)
    specific_start_date = models.DateField(null=True, blank=True) # do not use, use properties below
    specific_end_date = models.DateField(null=True, blank=True) # do not use, use properties below

    @property
    def start_date(self):
        if self.period_source == 'SERVICE':
            return self.service.start_date
        else:
            return self.specific_start_date
        
    @property
    def end_date(self):
        if self.period_source == 'SERVICE':
            return self.service.end_date
        else:
            return self.specific_end_date

    def get_absolute_url(self):
        return reverse("placement-detail", kwargs={"pk": self.pk})


class Service(models.Model):
    FIXED_PRICE = "FIXED_PRICE"
    PER_HOUR = "PER_HOUR"
    COST_TYPE_CHOICES = {
        FIXED_PRICE: "Vaste prijs",
        PER_HOUR: "Per uur",
    }

    ASSIGNMENT = "ASSIGNMENT"
    SERVICE = "SERVICE"
    PERIOD_SOURCE_CHOICES = {
        ASSIGNMENT: "Neem over van opdracht",
        SERVICE: "Specifiek voor dienst"
    }

    assignment = models.ForeignKey('Assignment', models.CASCADE, related_name='services')
    description = models.CharField(max_length=500)
    cost_type = models.CharField(max_length=20, choices=COST_TYPE_CHOICES, default=PER_HOUR)
    fixed_cost = models.IntegerField(null=True, blank=True)
    hours_per_week = models.IntegerField(null=True, blank=True)
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=ASSIGNMENT)
    specific_start_date = models.DateField(null=True, blank=True) # do not use, use properties below
    specific_end_date = models.DateField(null=True, blank=True) # do not use, use properties below
    # placements via reverse relation

    @property
    def start_date(self):
        if self.period_source == 'ASSIGNMENT':
            return self.assignment.start_date
        else:
            return self.specific_start_date
        
    @property
    def end_date(self):
        if self.period_source == 'ASSIGNMENT':
            return self.assignment.end_date
        else:
            return self.specific_end_date

    def get_total_cost(self):
        """Calculate total cost: aantal weken * uren per week * 100 euro/uur"""
        if not self.start_date or not self.end_date or not self.hours_per_week:
            return None
        
        # Calculate number of weeks
        delta = self.end_date - self.start_date
        weeks = delta.days / 7
        
        # Calculate total cost
        total_cost = weeks * self.hours_per_week * 100
        return round(total_cost, 2)

    def __str__(self):
        return f"{self.description} "

    def get_absolute_url(self):
        return reverse("service-detail", kwargs={"pk": self.pk})
