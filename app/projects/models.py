import uuid

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

TEAM_PENDING = 'Pending'
TEAM_READY = 'Ready'
TEAM_ACTIVE = 'Active'
TEAM_DEACTIVATED = 'Deactivated'

TEAM_STATUS = (
    (TEAM_PENDING, 'Pending'),
    (TEAM_READY, 'Ready to be activated'),
    (TEAM_ACTIVE, 'Activated'),
    (TEAM_DEACTIVATED, 'Deactivated')
)

SIGNED_FORM_PENDING_APPROVAL = 'P'
SIGNED_FORM_APPROVED = 'A'
SIGNED_FORM_REJECTED = 'R'

SIGNED_FORM_STATUSES = (
    (SIGNED_FORM_PENDING_APPROVAL, 'Pending Approval'),
    (SIGNED_FORM_APPROVED, 'Approved'),
    (SIGNED_FORM_REJECTED, 'Rejected'),
)

AGREEMENT_FORM_TYPE_STATIC = 'STATIC'
AGREEMENT_FORM_TYPE_EXTERNAL_LINK = 'EXTERNAL_LINK'

AGREEMENT_FORM_TYPE = (
    (AGREEMENT_FORM_TYPE_STATIC, 'STATIC'),
    (AGREEMENT_FORM_TYPE_EXTERNAL_LINK, 'EXTERNAL LINK')
)


def get_agreement_form_upload_path(instance, filename):

    form_directory = 'agreementforms/'
    file_name = uuid.uuid4()
    file_extension = filename.split('.')[-1]
    return '%s/%s.%s' % (form_directory, file_name, file_extension)

def get_submission_form_upload_path(instance, filename):

    form_directory = 'submissionforms/'
    file_name = uuid.uuid4()
    file_extension = filename.split('.')[-1]
    return '%s/%s.%s' % (form_directory, file_name, file_extension)

def get_institution_logo_upload_path(instance, filename):

    form_directory = 'institutionlogos/'
    file_name = uuid.uuid4()
    file_extension = filename.split('.')[-1]
    return '%s/%s.%s' % (form_directory, file_name, file_extension)


class Institution(models.Model):
    """
    This represents an institution such as a university that might be co-sponsoring a challenge.
    The logo image file should live under static/institutionlogos/.
    """

    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
    logo_path = models.CharField(max_length=300, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.name)


class AgreementForm(models.Model):
    """
    This represents the type of forms that a user might need to sign to be granted access to
    a data set, such as a data use agreement or rules of conduct. If this is derived from an
    html file, look at get_agreement_form_upload_path() to see where the file should be stored.
    If this agreement form lives on an external web page, supply the URL in the external_link
    field.
    """

    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
    short_name = models.CharField(max_length=6, blank=False, null=False)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    form_file_path = models.CharField(max_length=300, blank=True, null=True)
    external_link = models.CharField(max_length=300, blank=True, null=True)
    type = models.CharField(max_length=50, choices=AGREEMENT_FORM_TYPE, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.name)

    def clean(self):
        if self.type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK and self.form_file_path is not None:
            raise ValidationError("An external link form should not have the form file path field populated.")
        if self.type != AGREEMENT_FORM_TYPE_EXTERNAL_LINK and self.external_link is not None:
            raise ValidationError("If the form type is not an external link, the external link field should not be populated.")


class DataProject(models.Model):
    """
    This represents a data project that users can access, along with its permissions and requirements.
    """

    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of project", unique=False)
    project_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Project Key", unique=True)
    institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")

    # A comma delimited string of email addresses.
    project_supervisors = models.CharField(max_length=1024, blank=True, null=True, verbose_name="Project Supervisors (comma-delimited, no spaces)")

    # Set how the project should be accessed.
    visible = models.BooleanField(default=False, blank=False, null=False)
    registration_open = models.BooleanField(default=False, blank=False, null=False)
    requires_authorization = models.BooleanField(default=True, blank=False, null=False)

    # Which forms users need to sign before accessing any data.
    agreement_forms = models.ManyToManyField(AgreementForm, blank=True, related_name='data_project_agreement_forms')

    # Simply for highlighting projects that are challenges.
    is_challenge = models.BooleanField(default=False, blank=False, null=False)

    # Set whether users need to form teams before accessing data.
    has_teams = models.BooleanField(default=False, blank=False, null=False)

    show_jwt = models.BooleanField(default=False, blank=False, null=False)

    order = models.IntegerField(blank=True, null=True, help_text="Indicate an order (lowest number = highest order) for how the DataProjects should be listed.")

    def __str__(self):
        return '%s' % (self.project_key)


class SignedAgreementForm(models.Model):
    """
    This represents the fully signed agreement form.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    agreement_form = models.ForeignKey(AgreementForm, on_delete=models.PROTECT)
    project = models.ForeignKey(DataProject, on_delete=models.PROTECT)
    date_signed = models.DateTimeField(auto_now_add=True)
    agreement_text = models.TextField(blank=False)
    status = models.CharField(max_length=1, null=False, blank=False, default='P', choices=SIGNED_FORM_STATUSES)


class Team(models.Model):
    """
    This model describes a team of participants that are competing in a data challenge.
    """

    team_leader = models.ForeignKey(User, on_delete=models.PROTECT)
    data_project = models.ForeignKey(DataProject, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=TEAM_STATUS, default='Pending')

    class Meta:
        unique_together = ('team_leader', 'data_project',)

    def get_submissions(self):
        """
        Returns a queryset of the non-deleted ChallengeTaskSubmission records for this team.
        """

        participants = self.participant_set.all()

        return ChallengeTaskSubmission.objects.filter(
            participant__in=participants,
            deleted=False
        )

    def __str__(self):
        return '%s' % self.team_leader.email


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(DataProject, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.CASCADE)

    # TODO remove or consolidate all these fields
    team_wait_on_leader_email = models.CharField(max_length=100, blank=True, null=True)
    team_wait_on_leader = models.BooleanField(default=False)
    team_pending = models.BooleanField(default=False)
    team_approved = models.BooleanField(default=False)

    # TODO remove all these?
    def assign_pending(self, team):
        self.set_pending()
        self.team = team

    def assign_approved(self, team):
        self.set_approved()
        self.team = team

    def set_pending(self):
        self.team_pending = True
        self.team_wait_on_leader = False
        self.team_wait_on_leader_email = None
        self.team_approved = False

    def set_approved(self):
        self.team_approved = True
        self.team_wait_on_leader = False
        self.team_wait_on_leader_email = None
        self.team_pending = False

    def get_submissions(self):
        """
        Returns a queryset of the non-deleted ChallengeTaskSubmission records for this participant.
        """

        return ChallengeTaskSubmission.objects.filter(
            participant=self,
            deleted=False
        )

    def __str__(self):
        return '%s - %s' % (self.user, self.project)


class HostedFileSet(models.Model):
    """
    An optional grouping for hosted files within a project.
    """

    title = models.CharField(max_length=100, blank=False, null=False)
    project = models.ForeignKey(DataProject, on_delete=models.CASCADE)

    def __str__(self):
        return self.project.project_key + ': ' + self.title


class HostedFile(models.Model):
    """
    Tracks the files belonging to projects that users will be able to download.
    """

    project = models.ForeignKey(DataProject, on_delete=models.CASCADE)

    # This UUID should be used in all templates instead of the pk id.
    uuid = models.UUIDField(null=False, unique=True, editable=False, default=uuid.uuid4)

    # How the file should be displayed on the front end.
    long_name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=2000, blank=True, null=True)

    # Information for where to find the file in S3.
    file_name = models.CharField(max_length=100, blank=False, null=False)
    file_location = models.CharField(max_length=100, blank=False, null=False)

    # Files can optionally be grouped under a set within a project.
    hostedfileset = models.ForeignKey(HostedFileSet, blank=True, null=True, on_delete=models.SET_NULL)

    # Should the file appear on the front end (and when).
    enabled = models.BooleanField(default=False)
    opened_time = models.DateTimeField(blank=True, null=True)
    closed_time = models.DateTimeField(blank=True, null=True)

    order = models.IntegerField(blank=True, null=True, help_text="Indicate an order (lowest number = highest order) for files to appear within a DataProject.")

    def __str__(self):
        return '%s - %s' % (self.project, self.long_name)

    def clean(self):
        if self.opened_time is not None and self.closed_time is not None and (self.opened_time > self.closed_time or self.closed_time < self.opened_time):
            raise ValidationError("Closed time must be a datetime after opened time")


class HostedFileDownload(models.Model):
    """
    Tracks who is attempting to download a hosted file.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    hosted_file = models.ForeignKey(HostedFile, on_delete=models.PROTECT)
    download_date = models.DateTimeField(auto_now_add=True)


class TeamComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    text = models.CharField(max_length=2000, blank=False, null=False)

    def __str__(self):
        return '%s %s %s' % (self.user, self.team, self.date)


class ChallengeTask(models.Model):
    """
    Describes a task that a data challenge might require. User's submissions for tasks are captured
    in the ChallengeTaskSubmission model.
    """

    data_project = models.ForeignKey(DataProject, on_delete=models.CASCADE)

    # How should the task be displayed on the front end
    title = models.CharField(max_length=200, default=None, blank=False, null=False)
    description = models.CharField(max_length=2000, blank=True, null=True)

    # Optional path to an html file that contains a form that should be completed when uploading a task solution
    submission_form_file_path = models.CharField(max_length=300, blank=True, null=True)

    # If blank, allow infinite submissions
    max_submissions = models.IntegerField(default=1, blank=True, null=True, help_text="Leave blank if you want there to be no cap.")

    # Should the task appear on the front end (and when)
    enabled = models.BooleanField(default=False, blank=False, null=False)
    opened_time = models.DateTimeField(blank=True, null=True)
    closed_time = models.DateTimeField(blank=True, null=True)

    # Should supervisors be notified of submissions of this task
    notify_supervisors_of_submissions = models.BooleanField(default=False, blank=False, null=False, help_text="Sends a notification to any emails listed in the project's supervisors field.")

    def __str__(self):
        return '%s: %s' % (self.data_project.project_key, self.title)

    def clean(self):
        if self.opened_time is not None and self.closed_time is not None and (self.opened_time > self.closed_time or self.closed_time < self.opened_time):
            raise ValidationError("Closed time must be a datetime after opened time")


class ChallengeTaskSubmission(models.Model):
    """
    Captures the files that participants are submitting for their challenges. Through the Participant model
    you can get to what team and project this submission pertains to. The location field is for fileservice
    integration. The submission_form_answers field stores any answers a participant might provide when
    submitting their work.
    """

    challenge_task = models.ForeignKey(ChallengeTask, on_delete=models.PROTECT)
    participant = models.ForeignKey(Participant, on_delete=models.PROTECT)
    upload_date = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(null=False, unique=True, primary_key=True, default=None)
    location = models.CharField(max_length=12, default=None, blank=True, null=True)
    submission_info = models.TextField(default=None, blank=True, null=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % (self.uuid)


# TODO remove
class ParticipantProject(models.Model):
    """
    Used by the PayerDB. Is this still needed?
    """

    name = models.CharField(max_length=20)

    class Meta:
        abstract = True


class ChallengeTaskSubmissionDownload(models.Model):
    """
    Tracks who is attempting to download a submission file.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    submission = models.ForeignKey(ChallengeTaskSubmission, on_delete=models.PROTECT)
    download_date = models.DateTimeField(auto_now_add=True)
