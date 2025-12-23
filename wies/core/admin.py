from django.contrib import admin
from .models import Assignment, Colleague, Ministry, LabelCategory, Label, Placement, Service, Skill, User


class AssignmentAdmin(admin.ModelAdmin):
    pass

class ColleagueAdmin(admin.ModelAdmin):
    pass

class UserAdmin(admin.ModelAdmin):
    pass

class SkillAdmin(admin.ModelAdmin):
    pass

class MinistryAdmin(admin.ModelAdmin):
    pass

class LabelCategoryAdmin(admin.ModelAdmin):
    pass

class LabelAdmin(admin.ModelAdmin):
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
admin.site.register(LabelCategory, LabelCategoryAdmin)
admin.site.register(Label, LabelAdmin)
admin.site.register(Placement, PlacementAdmin)
admin.site.register(Service, ServiceAdmin)

