from django.contrib import admin

from .models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)


class AssignmentOrganizationUnitInline(admin.TabularInline):
    model = AssignmentOrganizationUnit
    extra = 1
    autocomplete_fields = ["organization"]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    inlines = [AssignmentOrganizationUnitInline]


@admin.register(Colleague)
class ColleagueAdmin(admin.ModelAdmin):
    search_fields = ["name", "email"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ["first_name", "last_name", "email"]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(LabelCategory)
class LabelCategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    pass


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    search_fields = ["colleague__name", "service__assignment__name"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    search_fields = ["assignment__name", "skill__name"]


@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(OrganizationUnit)
class OrganizationUnitAdmin(admin.ModelAdmin):
    search_fields = ["name"]
