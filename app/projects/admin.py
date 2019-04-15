from django.contrib import admin

from projects.models import DataProject
from projects.models import AgreementForm
from projects.models import SignedAgreementForm
from projects.models import Team
from projects.models import Participant
from projects.models import Institution
from projects.models import HostedFile
from projects.models import HostedFileSet
from projects.models import HostedFileDownload
from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission
from projects.models import ChallengeTaskSubmissionDownload

class DataProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'is_challenge', 'order')
    list_filter = ('is_challenge', )

class AgreementformAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'type', 'form_file_path')

class SignedagreementformAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed', 'status')

class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_leader', 'data_project')
    list_filter = ('data_project', )
    search_fields = ('data_project__project_key', 'team_leader__email')

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'team')
    list_filter = ('project', )
    search_fields = ('project__project_key', 'team__team_leader__email', 'user__email')

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_path')

class HostedFileAdmin(admin.ModelAdmin):
    list_display = ('long_name', 'project', 'hostedfileset', 'file_name', 'file_location', 'order')
    list_filter = ('project', )
    search_fields = ('project__project_key', 'file_name', )

class HostedFileSetAdmin(admin.ModelAdmin):
    list_display = ('title', 'project')

class HostedFileDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'hosted_file', 'download_date')

class ChallengeTaskAdmin(admin.ModelAdmin):
    list_display = ('data_project', 'title', 'enabled', 'opened_time', 'closed_time')

class ChallengeTaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ('participant', 'challenge_task', 'upload_date', 'uuid')
    list_filter = ('participant__project', 'challenge_task')
    search_fields = ('participant__project__project_key', 'participant__user__email', 'challenge_task__title')

class ChallengeTaskSubmissionDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'submission', 'download_date')

admin.site.register(DataProject, DataProjectAdmin)
admin.site.register(AgreementForm, AgreementformAdmin)
admin.site.register(SignedAgreementForm, SignedagreementformAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Institution, InstitutionAdmin)
admin.site.register(HostedFile, HostedFileAdmin)
admin.site.register(HostedFileSet, HostedFileSetAdmin)
admin.site.register(HostedFileDownload, HostedFileDownloadAdmin)
admin.site.register(ChallengeTask, ChallengeTaskAdmin)
admin.site.register(ChallengeTaskSubmission, ChallengeTaskSubmissionAdmin)
admin.site.register(ChallengeTaskSubmissionDownload, ChallengeTaskSubmissionDownloadAdmin)
