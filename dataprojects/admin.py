from django.contrib import admin
from .models import DataProject


class DataprojectsAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'project_url')

admin.site.register(DataProject, DataprojectsAdmin)
