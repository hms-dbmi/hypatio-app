import uuid

from django.db import models
from django.contrib.auth.models import User
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

def get_agreement_form_upload_path(instance, filename):

    form_directory = 'agreementforms/'
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
    """
    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
    logo = models.ImageField(upload_to=get_institution_logo_upload_path, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.name)


class AgreementForm(models.Model):
    """
    This represents the type of forms that a user might need to sign to be granted access to
    a data set, such as a data use agreement or rules of conduct. The form file should be an html file.
    """
    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
    short_name = models.CharField(max_length=6, blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)
    form_html = models.FileField(upload_to=get_agreement_form_upload_path, validators=[FileExtensionValidator(allowed_extensions=['html'])])

    def __str__(self):
        return '%s' % (self.name)


class DataProject(models.Model):
    """
    This represents a data project that users can access, along with its permissions and requirements.
    A DataProject can be simply a data set or it can be a data contest as recognized by the is_contest
    flag.
    """
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of project", unique=True)
    project_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Project Key", unique=True)
    institution = models.ForeignKey(Institution, blank=True, null=True, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")
    permission_scheme = models.CharField(max_length=100, default="PRIVATE", verbose_name="Permission Scheme")
    agreement_forms_required = models.BooleanField(default=True)
    agreement_forms = models.ManyToManyField(AgreementForm, blank=True, related_name='data_project_agreement_forms')
    project_supervisor = models.CharField(max_length=255, blank=True, null=True, verbose_name="Project Supervisor")
    # TODO change to a choice field and create an enumerable of options (contest, data project)
    is_contest = models.BooleanField(default=False, blank=False, null=False)
    visible = models.BooleanField(default=False, blank=False, null=False)
    registration_open = models.BooleanField(default=False, blank=False, null=False)
    accepting_user_submissions = models.BooleanField(default=False, blank=False, null=False)

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
    team_leader = models.OneToOneField(User)
    data_project = models.ForeignKey(DataProject)
    status = models.CharField(max_length=30, choices=TEAM_STATUS, default='Pending')

    def get_count_of_submissions_made(self):
        """Returns the total number of submissions that a team's participants have made for its challenge."""

        submissions = 0
        participants = self.participant_set.all()
        for p in participants:
            submissions += p.participantsubmission_set.count()
        return submissions

    def get_number_of_submissions_left(self):
        """Returns the number of submissions left that a team may make."""

        # TODO: abstract this number to the DataProjects class?
        return 3 - self.get_count_of_submissions_made()

    def __str__(self):
        return '%s' % self.team_leader.email


class Participant(models.Model):
    user = models.OneToOneField(User)
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

    def __str__(self):
        return '%s - %s' % (self.user, self.data_challenge)


class HostedFile(models.Model):
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
    """Captures the files that participants are submitting for their challenges. Through the Participant model
    you can get to what team and project this submission pertains to.
    """
    participant = models.ForeignKey(Participant)
    upload_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField()

    def __str__(self):
        return '%s %s' % (self.participant.user, self.file)
