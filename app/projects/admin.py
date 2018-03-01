from django.contrib import admin
from .models import DataProject
from .models import AgreementForm
from .models import SignedAgreementForm
from .models import Team
from .models import Participant
from .models import Institution
from .models import DataGate
from .models import HostedFile
from .models import HostedFileDownload

class DataprojectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'is_contest', 'project_supervisor') #, 'project_url')

class AgreementformAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'form_html')

class SignedagreementformAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed')

class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_leader', 'data_project')

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_challenge', 'team')

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')

class DataGateAdmin(admin.ModelAdmin):
    list_display = ('project', 'data_location_type', 'data_location')

class HostedFileAdmin(admin.ModelAdmin):
    list_display = ('long_name', 'project', 'file_name', 'file_location_type', 'file_location')

class HostedFileDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'hosted_file', 'download_date')

admin.site.register(DataProject, DataprojectAdmin)
admin.site.register(AgreementForm, AgreementformAdmin)
admin.site.register(SignedAgreementForm, SignedagreementformAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Institution, InstitutionAdmin)
admin.site.register(DataGate, DataGateAdmin)
admin.site.register(HostedFile, HostedFileAdmin)
admin.site.register(HostedFileDownload, HostedFileDownloadAdmin)