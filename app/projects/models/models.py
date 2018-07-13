import uuid

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

FILE_SERVICE_URL = 'FILE_SERVICE_URL'
EXTERNAL_APP_URL = 'EXTERNAL_APP_URL'
S3_BUCKET = 'S3_BUCKET'

DATA_LOCATION_TYPE = (
    (FILE_SERVICE_URL, 'FileService Signed URL'),
    (EXTERNAL_APP_URL, 'External Application URL'),
    (S3_BUCKET, 'S3 Bucket directly accessed by Hyatio')
)


TEAM_STATUS = (
    ('Pending', 'Pending'),
    ('Ready', 'Ready to be activated'),
    ('Active', 'Activated'),
    ('Deactivated', 'Deactivated')
)


SIGNED_FORM_STATUSES = (
    ('P', 'Pending Approval'),
    ('A', 'Approved'),
    ('R', 'Rejected'),
)

AGREEMENT_FORM_TYPE_STATIC = 'STATIC'
AGREEMENT_FORM_TYPE_DJANGO = 'DJANGO'
AGREEMENT_FORM_TYPE_EXTERNAL_LINK = 'EXTERNAL_LINK'

AGREEMENT_FORM_TYPE = (
    (AGREEMENT_FORM_TYPE_STATIC, 'STATIC'),
    (AGREEMENT_FORM_TYPE_DJANGO, 'DJANGO'),
    (AGREEMENT_FORM_TYPE_EXTERNAL_LINK, 'EXTERNAL LINK')
)


PERMISSION_SCHEME_PRIVATE = "PRIVATE"
PERMISSION_SCHEME_PUBLIC = "PUBLIC"
PERMISSION_SCHEME_EXTERNALLY_GRANTED = "EXTERNALLY_GRANTED"

PERMISSION_SCHEME = (
    (PERMISSION_SCHEME_PRIVATE, "PRIVATE"),
    (PERMISSION_SCHEME_PUBLIC, "PUBLIC"),
    (PERMISSION_SCHEME_EXTERNALLY_GRANTED, "EXTERNALLY_GRANTED")
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
    A DataProject can be simply a data set or it can be a data contest as recognized by the is_contest
    flag. The submission form file should be an html file that lives under static/submissionforms/.
    Project_supervisors should be a comma delimited string of email addresses.
    """

    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of project", unique=False)
    project_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Project Key", unique=True)
    institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")
    project_supervisors = models.CharField(max_length=1024, blank=True, null=True, verbose_name="Project Supervisors (comma-delimited, no spaces)")

    visible = models.BooleanField(default=False, blank=False, null=False)
    permission_scheme = models.CharField(max_length=100, default="PRIVATE", verbose_name="Permission Scheme")
    registration_open = models.BooleanField(default=False, blank=False, null=False)

    agreement_forms = models.ManyToManyField(AgreementForm, blank=True, related_name='data_project_agreement_forms')

    is_contest = models.BooleanField(default=False, blank=False, null=False)
    has_teams = models.BooleanField(default=False, blank=False, null=False)

    accepting_user_submissions = models.BooleanField(default=False, blank=False, null=False)
    submission_form_file_path = models.CharField(max_length=300, blank=True, null=True)

    show_jwt = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        return '%s' % (self.project_key)


class DataGate(models.Model):
    project = models.ForeignKey(DataProject)
    data_location_type = models.CharField(max_length=50, choices=DATA_LOCATION_TYPE)
    data_location = models.CharField(max_length=250)


class SignedAgreementForm(models.Model):
    """
    This represents the fully signed agreement form.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    agreement_form = models.ForeignKey(AgreementForm, on_delete=models.PROTECT)
    project = models.ForeignKey(DataProject)
    date_signed = models.DateTimeField(auto_now_add=True)
    agreement_text = models.TextField(blank=False)
    status = models.CharField(max_length=1, null=False, blank=False, default='P', choices=SIGNED_FORM_STATUSES)


class Team(models.Model):
    """
    This model describes a team of participants that are competing in a data challenge.
    """

    team_leader = models.ForeignKey(User)
    data_project = models.ForeignKey(DataProject)
    status = models.CharField(max_length=30, choices=TEAM_STATUS, default='Pending')

    class Meta:
        unique_together = ('team_leader', 'data_project',)

    def get_count_of_submissions_made(self):
        """
        Returns the total number of submissions that a team's participants have made for its challenge.
        """

        submissions = self.get_submissions().count()
        return submissions

    def get_number_of_submissions_left(self):
        """
        Returns the number of submissions left that a team may make.
        """

        # TODO: abstract this number to the DataProjects class?
        return 3 - self.get_count_of_submissions_made()

    def get_submissions(self):
        """
        Returns a queryset of the non-deleted ParticipantSubmission records for this team.
        """

        participants = self.participant_set.all()

        return ParticipantSubmission.objects.filter(
            participant__in=participants,
            deleted=False
        )

    def __str__(self):
        return '%s' % self.team_leader.email


class Participant(models.Model):
    user = models.ForeignKey(User)
    data_challenge = models.ForeignKey(DataProject)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.CASCADE)
    team_wait_on_leader_email = models.CharField(max_length=100, blank=True, null=True)
    team_wait_on_leader = models.BooleanField(default=False)
    team_pending = models.BooleanField(default=False)
    team_approved = models.BooleanField(default=False)

    @property
    def is_on_team(self):
        return self.team is not None and self.team_approved

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
        Returns a queryset of the non-deleted ParticipantSubmission records for this participant.
        """

        return ParticipantSubmission.objects.filter(
            participant=self,
            deleted=False
        )

    def __str__(self):
        return '%s - %s' % (self.user, self.data_challenge)

class HostedFile(models.Model):
    """
    Tracks the files belonging to projects that users will be able to download.
    """

    long_name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=2000, blank=True, null=True)
    file_name = models.CharField(max_length=100, blank=False, null=False)
    file_location_type = models.CharField(max_length=100, blank=False, null=False, choices=DATA_LOCATION_TYPE)
    file_location = models.CharField(max_length=100, blank=False, null=False)
    project = models.ForeignKey(DataProject)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return '%s - %s' % (self.project, self.long_name)

class HostedFileDownload(models.Model):
    """
    Tracks who is attempting to download a hosted file.
    """

    user = models.ForeignKey(User)
    hosted_file = models.ForeignKey(HostedFile)
    download_date = models.DateTimeField(auto_now_add=True)

class TeamComment(models.Model):
    user = models.ForeignKey(User)
    team = models.ForeignKey(Team)
    date = models.DateTimeField(auto_now_add=True)
    text = models.CharField(max_length=2000, blank=False, null=False)

    def __str__(self):
        return '%s %s %s' % (self.user, self.team, self.date)

class ParticipantSubmission(models.Model):
    """
    Captures the files that participants are submitting for their challenges. Through the Participant model
    you can get to what team and project this submission pertains to. The location field is for fileservice
    integration. The submission_form_answers field stores any answers a participant might provide when
    submitting their work.
    """
    participant = models.ForeignKey(Participant)
    upload_date = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(null=False, unique=True, primary_key=True, default=None)
    location = models.CharField(max_length=12, default=None, blank=True, null=True)
    submission_info = models.TextField(default=None, blank=True, null=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % (self.uuid)


class ParticipantProject(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        abstract = True


class TeamSubmissionsDownload(models.Model):
    """
    Tracks who is attempting to download a team's submissions.
    """

    user = models.ForeignKey(User)
    team = models.ForeignKey(Team)
    participant_submissions = models.ManyToManyField(ParticipantSubmission)
    download_date = models.DateTimeField(auto_now_add=True)
