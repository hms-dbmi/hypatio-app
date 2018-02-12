import uuid

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


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
    # TODO add form validation to check for html goodness
    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
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

    def __str__(self):
        return '%s %s' % (self.project_key, self.name)


class SignedAgreementForm(models.Model):
    """
    This represents the fully signed agreement form.
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    agreement_form = models.ForeignKey(AgreementForm, on_delete=models.PROTECT)
    project = models.ForeignKey(DataProject)
    date_signed = models.DateTimeField(auto_now_add=True)
    agreement_text = models.TextField(blank=False)


class Team(models.Model):
    team_leader = models.OneToOneField(User)
    data_project = models.ForeignKey(DataProject)

    def __str__(self):
        return '%s' % self.team_leader.email


class Participant(models.Model):
    user = models.OneToOneField(User)
    data_challenge = models.ForeignKey(DataProject)
    team = models.ForeignKey(Team, null=True, blank=True)
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
