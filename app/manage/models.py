from django.db import models
from django.contrib.auth.models import User

from projects.models import DataProject
from projects.models import ChallengeTask
from projects.models import ChallengeTaskSubmission


class ChallengeTaskSubmissionExport(models.Model):
    """
    Captures the files that are generated as an export for admins.
    """

    data_project = models.ForeignKey(DataProject, on_delete=models.PROTECT)
    challenge_tasks = models.ManyToManyField(ChallengeTask)
    challenge_task_submissions = models.ManyToManyField(ChallengeTaskSubmission)
    requester = models.ForeignKey(User, on_delete=models.PROTECT)
    request_date = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(null=False, unique=True, primary_key=True, default=None)
    location = models.CharField(max_length=12, default=None, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.uuid)
