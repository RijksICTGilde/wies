from django.contrib import admin
from .models import ExactEmployee, ExactProject


@admin.register(ExactEmployee)
class ExactEmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'naam_medewerker', 
        'rin_nummer', 
        'aantal_uren', 
        'schaalniveau', 
        'organisatieonderdeel', 
        'status'
    ]
    list_filter = ['status', 'if_kf', 'schaalniveau', 'uren_schrijven']
    search_fields = ['naam_medewerker', 'rin_nummer', 'email', 'organisatieonderdeel']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basisgegevens', {
            'fields': (
                'naam_medewerker',
                'rin_nummer', 
                'aantal_uren',
                'schaalniveau',
                'kostenplaats',
                'if_kf'
            )
        }),
        ('RC Gegevens', {
            'fields': (
                'uren_schrijven',
                'email',
                'organisatieonderdeel',
                'manager',
                'status'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ExactProject)
class ExactProjectAdmin(admin.ModelAdmin):
    list_display = [
        'projectnaam',
        'start_datum',
        'eind_datum', 
        'aantal_uur',
        'tarief',
        'total_value',
        'type_project'
    ]
    list_filter = [
        'type_project', 
        'contract_eenzijdig_getekend', 
        'contract_tweezijdig_getekend',
        'start_datum'
    ]
    search_fields = [
        'projectnaam', 
        'odi_thema', 
        'organisatieonderdeel', 
        'uw_referentie'
    ]
    readonly_fields = ['created_at', 'updated_at', 'total_value']
    date_hierarchy = 'start_datum'
    
    fieldsets = (
        ('Project Basis', {
            'fields': (
                'projectnaam',
                'odi_thema',
                'product_dienst_assortiment',
                'start_datum',
                'eind_datum',
                'aantal_uur',
                'tarief'
            )
        }),
        ('RC Gegevens', {
            'fields': (
                'type_project',
                'organisatieonderdeel',
                'manager',
                'moeder'
            )
        }),
        ('Contract', {
            'fields': (
                'contract_besteld_door',
                'contract_contactpersoon',
                'contract_factuur_voor',
                'contract_ter_attentie_van',
                'contract_eenzijdig_getekend',
                'contract_tweezijdig_getekend'
            )
        }),
        ('Referenties', {
            'fields': (
                'uw_referentie',
                'uw_kenmerk'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'total_value'),
            'classes': ('collapse',)
        })
    )