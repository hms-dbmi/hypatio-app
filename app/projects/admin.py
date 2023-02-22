from django.contrib import admin
from django.urls import reverse
from django.utils.html import escape, mark_safe

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
from projects.models import NLPDUASignedAgreementFormFields
from projects.models import NLPWHYSignedAgreementFormFields
from projects.models import DUASignedAgreementFormFields
from projects.models import ROCSignedAgreementFormFields
from projects.models import MAYOSignedAgreementFormFields
from projects.models import MIMIC3SignedAgreementFormFields

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


class SignedAgreementFormFieldsAdmin(admin.ModelAdmin):
    def get_user(self, obj):
        return obj.signed_agreement_form.user.email
    get_user.short_description = 'User'
    get_user.admin_order_field = 'signed_agreement_form__user__email'

    def get_status(self, obj):
        return obj.signed_agreement_form.status
    get_status.short_description = 'Status'
    get_status.admin_order_field = 'signed_agreement_form__status'

    def signed_agreement_form_link(self, obj):
        link = reverse("admin:projects_signedagreementform_change", args=[obj.signed_agreement_form.id])
        return mark_safe(f'<a href="{link}">{escape(obj.signed_agreement_form.__str__())}</a>')

    signed_agreement_form_link.short_description = 'Signed Agreement Form'
    signed_agreement_form_link.admin_order_field = 'signed agreement form'

    list_display = (
        'get_user',
        'get_status',
        'signed_agreement_form_link'
        )
    search_fields = (
        'signed_agreement_form__user__email',
        'signed_agreement_form__agreement_form__project',
        'signed_agreement_form__agreement_form__short_name',
        'signed_agreement_form',
        )
    readonly_fields = (
        'signed_agreement_form',
        'created',
        'modified'
        )


class NLPDUASignedAgreementFormFieldsAdmin(SignedAgreementFormFieldsAdmin):
    pass


class NLPWHYSignedAgreementFormFieldsAdmin(SignedAgreementFormFieldsAdmin):
    pass


class DUASignedAgreementFormFieldsAdmin(SignedAgreementFormFieldsAdmin):
    pass


class ROCSignedAgreementFormFieldsAdmin(SignedAgreementFormFieldsAdmin):
    pass


class MAYOSignedAgreementFormFieldsAdmin(SignedAgreementFormFieldsAdmin):
    pass


class MIMIC3SignedAgreementFormFieldsAdmin(SignedAgreementFormFieldsAdmin):
    pass


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


admin.site.register(NLPDUASignedAgreementFormFields, NLPDUASignedAgreementFormFieldsAdmin)
admin.site.register(NLPWHYSignedAgreementFormFields, NLPWHYSignedAgreementFormFieldsAdmin)
admin.site.register(DUASignedAgreementFormFields, DUASignedAgreementFormFieldsAdmin)
admin.site.register(ROCSignedAgreementFormFields, ROCSignedAgreementFormFieldsAdmin)
admin.site.register(MAYOSignedAgreementFormFields, MAYOSignedAgreementFormFieldsAdmin)
admin.site.register(MIMIC3SignedAgreementFormFields, MIMIC3SignedAgreementFormFieldsAdmin)
