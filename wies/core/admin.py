from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Assignment, Colleague, Ministry, Brand, Placement, Service, Skill


class AssignmentAdmin(admin.ModelAdmin):
    pass

class SkillAdmin(admin.ModelAdmin):
    pass

class MinistryAdmin(admin.ModelAdmin):
    pass

class BrandAdmin(admin.ModelAdmin):
    pass


class PlacementAdmin(admin.ModelAdmin):
    pass

class ServiceAdmin(admin.ModelAdmin):
    pass


admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(Colleague, UserAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Ministry, MinistryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Placement, PlacementAdmin)
admin.site.register(Service, ServiceAdmin)
