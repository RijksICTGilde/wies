from django.contrib import admin
from projects.models import Assignment
from projects.models import Colleague


class AssignmentAdmin(admin.ModelAdmin):
    pass

class ColleagueAdmin(admin.ModelAdmin):
    pass


admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(Colleague, ColleagueAdmin)
