from django.contrib import admin
from .models import DataProject, DataUseAgreement, DataUseAgreementSign

class DataprojectsAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'project_url')

class DatauseagreementAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'agreement_form_file')

class DatauseagreementsignAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_use_agreement', 'date_signed')

admin.site.register(DataProject, DataprojectsAdmin)
admin.site.register(DataUseAgreement, DatauseagreementAdmin)
admin.site.register(DataUseAgreementSign, DatauseagreementsignAdmin)
