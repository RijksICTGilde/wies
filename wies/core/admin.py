from django.contrib import admin
from .models import Assignment, Colleague, EmailAlias, Ministry, Brand, Placement, Service, Skill, User


class AssignmentAdmin(admin.ModelAdmin):
    pass

class ColleagueAdmin(admin.ModelAdmin):
    pass

class EmailAliasInline(admin.TabularInline):
    model = EmailAlias
    extra = 1

class UserAdmin(admin.ModelAdmin):
    inlines = [EmailAliasInline]

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
admin.site.register(Colleague, ColleagueAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Ministry, MinistryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Placement, PlacementAdmin)
admin.site.register(Service, ServiceAdmin)

