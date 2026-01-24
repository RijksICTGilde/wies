from django.contrib import admin

from .models import Assignment, Colleague, Label, LabelCategory, Ministry, Placement, Service, Skill, User


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    pass


@admin.register(Colleague)
class ColleagueAdmin(admin.ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    pass


@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    pass


@admin.register(LabelCategory)
class LabelCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "display_order"]
    ordering = ["display_order", "name"]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    pass


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    pass


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    pass
