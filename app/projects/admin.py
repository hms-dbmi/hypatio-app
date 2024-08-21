from django.contrib import admin
from django.urls import reverse
from django.utils.html import escape, mark_safe

from projects.models import Group
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
from projects.models import Bucket
from projects.models import InstitutionalOfficial
from projects.models import InstitutionalMember


class GroupAdmin(admin.ModelAdmin):
    list_display = ('title', 'key', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )


class BucketAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )


class DataProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_key', 'informational_only', 'registration_open', 'requires_authorization', 'is_challenge', 'order', 'created', 'modified', )
    list_filter = ('informational_only', 'registration_open', 'requires_authorization', 'is_challenge')
    readonly_fields = ('created', 'modified', )

class AgreementformAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'type', 'form_file_path', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )

class SignedagreementformAdmin(admin.ModelAdmin):
    list_display = ('user', 'agreement_form', 'date_signed', 'status', 'created', 'modified', )
    search_fields = ('user__email', )
    readonly_fields = ('created', 'modified', )

class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_leader', 'data_project', 'created', 'modified', )
    list_filter = ('data_project', )
    search_fields = ('data_project__project_key', 'team_leader__email')
    readonly_fields = ('created', 'modified', )

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'team', 'created', 'modified', )
    list_filter = ('project', )
    search_fields = ('project__project_key', 'team__team_leader__email', 'user__email')
    readonly_fields = ('created', 'modified', )

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_path', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )

class InstitutionalOfficialAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'project', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )

class InstitutionalMemberAdmin(admin.ModelAdmin):
    list_display = ('email', 'official', 'user', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )

class HostedFileAdmin(admin.ModelAdmin):
    list_display = ('long_name', 'project', 'hostedfileset', 'file_name', 'file_location', 'order', 'created', 'modified',)
    list_filter = ('project', )
    search_fields = ('project__project_key', 'file_name', )
    readonly_fields = ('created', 'modified', )

class HostedFileSetAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'order', 'created', 'modified', )
    list_filter = ('project', )
    readonly_fields = ('created', 'modified', )

class HostedFileDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'hosted_file', 'download_date')
    search_fields = ('user__email', )

class ChallengeTaskAdmin(admin.ModelAdmin):
    list_display = ('data_project', 'title', 'enabled', 'opened_time', 'closed_time', 'created', 'modified', )
    readonly_fields = ('created', 'modified', )

class ChallengeTaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ('participant', 'challenge_task', 'upload_date', 'uuid', )
    list_filter = ('participant__project', 'challenge_task')
    search_fields = ('participant__project__project_key', 'participant__user__email', 'challenge_task__title')

class ChallengeTaskSubmissionDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'submission', 'download_date')
    search_fields = ('user__email', )


admin.site.register(Group, GroupAdmin)
admin.site.register(Bucket, BucketAdmin)
admin.site.register(DataProject, DataProjectAdmin)
admin.site.register(AgreementForm, AgreementformAdmin)
admin.site.register(SignedAgreementForm, SignedagreementformAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Institution, InstitutionAdmin)
admin.site.register(InstitutionalOfficial, InstitutionalOfficialAdmin)
admin.site.register(InstitutionalMember, InstitutionalMemberAdmin)
admin.site.register(HostedFile, HostedFileAdmin)
admin.site.register(HostedFileSet, HostedFileSetAdmin)
admin.site.register(HostedFileDownload, HostedFileDownloadAdmin)
admin.site.register(ChallengeTask, ChallengeTaskAdmin)
admin.site.register(ChallengeTaskSubmission, ChallengeTaskSubmissionAdmin)
admin.site.register(ChallengeTaskSubmissionDownload, ChallengeTaskSubmissionDownloadAdmin)
