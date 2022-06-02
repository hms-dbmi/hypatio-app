from django.contrib import admin

from manage.models import ChallengeTaskSubmissionExport


class ChallengeTaskSubmissionExportAdmin(admin.ModelAdmin):
    list_display = ('data_project', 'requester', 'request_date', 'uuid', )
    list_filter = ('data_project', 'requester', )


admin.site.register(ChallengeTaskSubmissionExport, ChallengeTaskSubmissionExportAdmin)
