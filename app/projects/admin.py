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
from .models import ChallengeTask
from .models import ChallengeTaskSubmission
from .models import TeamSubmissionsDownload
from .models import PayerDBForm

class DataprojectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'is_contest')
    list_filter = ('is_contest', )

class AgreementformAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'type', 'form_file_path')

class SignedagreementformAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed', 'status')

class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_leader', 'data_project')
    list_filter = ('data_project', )
    search_fields = ('data_project__project_key', 'team_leader__email')

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_challenge', 'team')
    list_filter = ('data_challenge', )
    search_fields = ('data_challenge__project_key', 'team__team_leader__email', 'user__email')

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_path')

class DataGateAdmin(admin.ModelAdmin):
    list_display = ('project', 'data_location_type', 'data_location')

class HostedFileAdmin(admin.ModelAdmin):
    list_display = ('long_name', 'project', 'file_name', 'file_location_type', 'file_location')
    list_filter = ('project', )
    search_fields = ('project__project_key', 'file_name', )

class HostedFileDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'hosted_file', 'download_date')

class ChallengeTaskAdmin(admin.ModelAdmin):
    list_display = ('data_project', 'title', 'enabled', 'opened_time', 'closed_time')

class ChallengeTaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ('participant', 'challenge_task', 'upload_date', 'uuid')
    list_filter = ('participant__data_challenge', 'challenge_task')
    search_fields = ('participant__data_challenge__project_key', 'participant__user__email', 'challenge_task__title')

class TeamSubmissionsDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'download_date')

class PayerDBFormAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed', 'status')


admin.site.register(DataProject, DataprojectAdmin)
admin.site.register(AgreementForm, AgreementformAdmin)
admin.site.register(SignedAgreementForm, SignedagreementformAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Institution, InstitutionAdmin)
admin.site.register(DataGate, DataGateAdmin)
admin.site.register(HostedFile, HostedFileAdmin)
admin.site.register(HostedFileDownload, HostedFileDownloadAdmin)
admin.site.register(ChallengeTask, ChallengeTaskAdmin)
admin.site.register(ChallengeTaskSubmission, ChallengeTaskSubmissionAdmin)
admin.site.register(TeamSubmissionsDownload, TeamSubmissionsDownloadAdmin)
admin.site.register(PayerDBForm, PayerDBFormAdmin)
