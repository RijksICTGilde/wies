from django.contrib import admin
from projects.models import Project
from projects.models import Colleague


class ProjectAdmin(admin.ModelAdmin):
    pass

class ColleagueAdmin(admin.ModelAdmin):
    pass


admin.site.register(Project, ProjectAdmin)
admin.site.register(Colleague, ColleagueAdmin)
