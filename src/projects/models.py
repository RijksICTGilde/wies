from django.db import models
from django.urls import reverse

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField()  #TODO: timezone aware

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

class Colleague(models.Model):
    name = models.CharField(max_length=200)
    function = models.CharField(max_length=200)

    def get_absolute_url(self):
        return reverse("colleague-detail", kwargs={"pk": self.pk})
