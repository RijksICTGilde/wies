from django.contrib import admin

from .models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)


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


@admin.register(LabelCategory)
class LabelCategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    pass


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    pass


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    pass


@admin.register(OrganizationUnit)
class OrganizationUnitAdmin(admin.ModelAdmin):
    list_display = ["name", "abbreviations_display", "organization_type", "parent", "is_active"]
    list_filter = ["organization_type", "is_active"]
    search_fields = ["name", "abbreviations"]
    raw_id_fields = ["parent", "successor"]

    @admin.display(description="Afkortingen")
    def abbreviations_display(self, obj):
        return ", ".join(obj.abbreviations) if obj.abbreviations else "-"


@admin.register(AssignmentOrganizationUnit)
class AssignmentOrganizationUnitAdmin(admin.ModelAdmin):
    list_display = ["assignment", "organization", "role"]
    list_filter = ["role"]
    raw_id_fields = ["assignment", "organization"]
