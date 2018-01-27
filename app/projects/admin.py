from django.contrib import admin
from .models import DataProject
from .models import AgreementForm
from .models import SignedAgreementForm

class DataprojectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'is_contest', 'project_supervisor') #, 'project_url')

class AgreementformAdmin(admin.ModelAdmin):
    list_display = ('name', 'form_html')

class SignedagreementformAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed', 'agreement_text')

admin.site.register(DataProject, DataprojectAdmin)
admin.site.register(AgreementForm, AgreementformAdmin)
admin.site.register(SignedAgreementForm, SignedagreementformAdmin)
