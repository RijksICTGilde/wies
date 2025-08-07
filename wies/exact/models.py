from django.db import models
from django.urls import reverse


class ExactEmployee(models.Model):
    IF_KF_CHOICES = [
        ('IF', 'IF'),
        ('KF', 'KF'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIEF', 'Actief'),
        ('INACTIEF', 'Inactief'),
        ('VERLOF', 'Verlof'),
        ('UITDIENST', 'Uit dienst'),
    ]
    
    naam_medewerker = models.CharField(max_length=200, verbose_name="Naam medewerker")
    aantal_uren = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Aantal uren")
    rin_nummer = models.CharField(max_length=20, unique=True, verbose_name="RIN nummer")
    schaalniveau = models.CharField(max_length=10, verbose_name="Schaalniveau")
    kostenplaats = models.CharField(max_length=50, verbose_name="Kostenplaats")
    if_kf = models.CharField(max_length=2, choices=IF_KF_CHOICES, verbose_name="IF/KF")
    uren_schrijven = models.BooleanField(default=True, verbose_name="Uren schrijven - nodig voor RC")
    email = models.EmailField(verbose_name="E-mail - gebruikt door RC")
    organisatieonderdeel = models.CharField(max_length=100, verbose_name="Organisatieonderdeel - gebruikt door RC")
    manager = models.CharField(max_length=200, verbose_name="Manager - gebruikt door RC")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIEF', verbose_name="Status - gebruikt door RC")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['naam_medewerker']
        verbose_name = 'Exact Employee'
        verbose_name_plural = 'Exact Employees'
    
    def __str__(self):
        return self.naam_medewerker
    
    def get_absolute_url(self):
        return reverse('exact:employee-detail', kwargs={'pk': self.pk})


class ExactProject(models.Model):
    TYPE_CHOICES = [
        ('INTERN', 'Intern'),
        ('EXTERN', 'Extern'),
        ('OVERHEID', 'Overheid'),
    ]
    
    projectnaam = models.CharField(max_length=200, verbose_name="Projectnaam")
    odi_thema = models.CharField(max_length=100, verbose_name="ODI thema")
    product_dienst_assortiment = models.CharField(max_length=150, verbose_name="Product/dienst assortiment")
    start_datum = models.DateField(verbose_name="Start datum")
    eind_datum = models.DateField(verbose_name="Eind datum")
    aantal_uur = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Aantal uur")
    tarief = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Tarief")
    type_project = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type - gebruikt door RC")
    organisatieonderdeel = models.CharField(max_length=100, verbose_name="Organisatieonderdeel - gebruikt door RC")
    manager = models.CharField(max_length=200, verbose_name="Manager - gebruikt door RC")
    moeder = models.CharField(max_length=200, blank=True, verbose_name="Moeder - gebruikt door RC")
    
    # Contract fields
    contract_besteld_door = models.CharField(max_length=200, verbose_name="Contract: Besteld door")
    contract_contactpersoon = models.CharField(max_length=200, verbose_name="Contract: contactpersoon opdrachtgever")
    contract_factuur_voor = models.CharField(max_length=200, verbose_name="Contract: Factuur voor")
    contract_ter_attentie_van = models.CharField(max_length=200, verbose_name="Contract: Ter attentie van")
    contract_eenzijdig_getekend = models.BooleanField(default=False, verbose_name="Contract: 1-zijdig getekend")
    contract_tweezijdig_getekend = models.BooleanField(default=False, verbose_name="Contract: 2-zijdig getekend")
    
    # Reference fields
    uw_referentie = models.CharField(max_length=100, verbose_name="Uw referentie - nodig voor contractafhandeling")
    uw_kenmerk = models.CharField(max_length=100, verbose_name="Uw kenmerk - nodig voor contractafhandeling")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['projectnaam']
        verbose_name = 'Exact Project'
        verbose_name_plural = 'Exact Projects'
    
    def __str__(self):
        return self.projectnaam
    
    def get_absolute_url(self):
        return reverse('exact:project-detail', kwargs={'pk': self.pk})
    
    @property
    def total_value(self):
        """Calculate total project value: aantal_uur * tarief"""
        return self.aantal_uur * self.tarief