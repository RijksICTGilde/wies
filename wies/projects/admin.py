from django.contrib import admin
from .models import Assignment, Colleague, Skill, Ministry, Brand, Expertise, Placement, Service


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'ministry', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'ministry', 'assignment_type']
    search_fields = ['name', 'organization', 'ministry__name']
    list_select_related = ['ministry']
    date_hierarchy = 'start_date'
    ordering = ['-start_date']

class ColleagueAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'source']
    list_filter = ['brand', 'source', 'expertises']
    search_fields = ['name']
    list_select_related = ['brand']
    filter_horizontal = ['skills', 'expertises']

class SkillAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class MinistryAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation']
    search_fields = ['name', 'abbreviation']

class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class ExpertiseAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class PlacementAdmin(admin.ModelAdmin):
    list_display = ['colleague', 'service', 'hours_per_week', 'start_date', 'end_date']
    list_filter = ['service__assignment__status', 'colleague__brand']
    search_fields = ['colleague__name', 'service__assignment__name']
    list_select_related = ['colleague', 'service__assignment']

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['description', 'assignment', 'skill', 'cost_type', 'hours_per_week']
    list_filter = ['cost_type', 'skill', 'assignment__status']
    search_fields = ['description', 'assignment__name']
    list_select_related = ['assignment', 'skill']


admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(Colleague, ColleagueAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Ministry, MinistryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Expertise, ExpertiseAdmin)
admin.site.register(Placement, PlacementAdmin)
admin.site.register(Service, ServiceAdmin)

