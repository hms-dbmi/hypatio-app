from django.contrib import admin
from .models import DataProject
from .models import AgreementForm
from .models import SignedAgreementForm
from .models import Team
from .models import Participant

class DataprojectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'is_contest', 'project_supervisor') #, 'project_url')

class AgreementformAdmin(admin.ModelAdmin):
    list_display = ('name', 'form_html')

class SignedagreementformAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed')

class TeamAdmin(admin.ModelAdmin):
    list_display = ('principal_investigator', 'data_project')

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_challenge', 'team')

admin.site.register(DataProject, DataprojectAdmin)
admin.site.register(AgreementForm, AgreementformAdmin)
admin.site.register(SignedAgreementForm, SignedagreementformAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Participant, ParticipantAdmin)
