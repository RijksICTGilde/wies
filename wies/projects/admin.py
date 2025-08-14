from django.contrib import admin
from .models import Assignment, Colleague, Skill, Ministry, Brand, Expertise, Placement, Service


class AssignmentAdmin(admin.ModelAdmin):
    pass

class ColleagueAdmin(admin.ModelAdmin):
    pass

class SkillAdmin(admin.ModelAdmin):
    pass

class MinistryAdmin(admin.ModelAdmin):
    pass

class BrandAdmin(admin.ModelAdmin):
    pass

class ExpertiseAdmin(admin.ModelAdmin):
    pass

class PlacementAdmin(admin.ModelAdmin):
    pass

class ServiceAdmin(admin.ModelAdmin):
    pass


admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(Colleague, ColleagueAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Ministry, MinistryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Expertise, ExpertiseAdmin)
admin.site.register(Placement, PlacementAdmin)
admin.site.register(Service, ServiceAdmin)

