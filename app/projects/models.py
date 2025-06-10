import uuid
import re
import importlib
from datetime import datetime
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import JSONField
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

import projects

import logging
logger = logging.getLogger(__name__)


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
AGREEMENT_FORM_TYPE_MODEL = 'MODEL'
AGREEMENT_FORM_TYPE_FILE = 'FILE'
AGREEMENT_FORM_TYPE_BLANK = 'BLANK'

AGREEMENT_FORM_TYPE = (
    (AGREEMENT_FORM_TYPE_STATIC, 'STATIC'),
    (AGREEMENT_FORM_TYPE_EXTERNAL_LINK, 'EXTERNAL LINK'),
    (AGREEMENT_FORM_TYPE_MODEL, 'MODEL'),
    (AGREEMENT_FORM_TYPE_FILE, 'FILE'),
    (AGREEMENT_FORM_TYPE_BLANK, 'BLANK'),
)

FILE_TYPE_ZIP = "zip"
FILE_TYPE_PDF = "pdf"

FILES_TYPES = (
    (FILE_TYPE_ZIP, "ZIP"),
    (FILE_TYPE_PDF, "PDF"),
)

FILES_CONTENT_TYPES = {
    FILE_TYPE_ZIP: ["application/zip", "application/x-zip-compressed", "multipart/x-zip", "application/x-zip"],
    FILE_TYPE_PDF: ["application/pdf", "application/x-pdf"],
}



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


class Bucket(models.Model):
    """
    An object store for project files.
    """

    class Provider(models.TextChoices):
        S3 = 's3', _('AWS S3')

    name = models.CharField(max_length=255, blank=False, null=False)
    default = models.BooleanField(default=False)
    provider = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        choices=Provider.choices,
        default=Provider.S3,
    )

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):

        # Check for multiple defaults
        if self.default and Bucket.objects.filter(default=True):
            raise ValidationError('Only one bucket may be configured as the default at one time.')

        # Check bucket for needed permissions
        try:
            match self.provider:
                case Bucket.Provider.S3:
                    try:
                        # Get the s3 client
                        s3 = boto3.client("s3")

                        # Download the test file
                        s3.list_objects_v2(
                            Bucket=self.name,
                        )

                        # Create a test file
                        key = f"test.{uuid.uuid4()}.txt"
                        s3.put_object(
                            Body="This is a test file.",
                            Bucket=self.name,
                            Key=key,
                        )

                        # Download the test file
                        s3.get_object(
                            Bucket=self.name,
                            Key=key,
                        )

                        # Delete the test file
                        s3.delete_object(
                            Bucket=self.name,
                            Key=key,
                        )

                    except ClientError as e:
                        logger.exception(f"Bucket permissions error: {e.response}")
                        raise ValidationError('This application has not been granted sufficient permissions on the bucket. Check logs for more info.')

                case _:
                    raise ValidationError('This application has not implemented validation for the specified bucket provider.')

        except Exception as e:
            logger.exception(f"Bucket check error: {e}", exc_info=True)
            raise ValidationError('This application could not verify sufficient bucket permissions. Check logs for more info.')

    @property
    def uri(self):
        return f"{self.provider}://{self.name}"

    @classmethod
    def get_default_pk(cls):
        """
        Returns the primary key of the default bucket. If this bucket does not
        exist, it is created using the S3_BUCKET parameter in settings.

        :return: The primary key of the default bucket
        :rtype: int
        """
        bucket, created = cls.objects.get_or_create(
            name=settings.S3_BUCKET,
            default=True,
            provider=Bucket.Provider.S3,
        )

        # Log if created
        if created:
            logger.info(f"Default bucket '{bucket.provider}://{bucket.name}' was created")

        return bucket.pk

    @classmethod
    def split_uri(cls, uri):
        """
        Accepts a bucket object's URI and splits it into three components:
        provider, bucket and key. These three values are returned as a tuple.
        The provider is converted to an instance of Bucket.Provider. If the
        passed URI contains an unsupported provider, an exception is raised.

        :param uri: The URI of the object
        :type uri: str
        :raises ValueError: Raises an error if the URI is invalid
        :raises ValueError: Raises an error if the URI's provider is unsupported
        :return: Returns a tuple of the URI's components
        :rtype: Bucket.Provider, str, str
        """
        provider = None
        try:
            # Separate URI
            pattern = r"(\w+):\/\/([^:\/\/]+?)\/(.+)"
            provider, bucket, key = re.match(pattern, uri).groups()

            return Bucket.Provider(provider.lower()), bucket, key

        except ValueError:
            raise ValueError(f"Unsupported bucket provider: '{provider}'")

        except Exception as e:
            logger.exception(f"Invalid file URI '{uri}': {e}")
            raise ValueError(f"Invalid file URI: '{uri}'")


class Institution(models.Model):
    """
    This represents an institution such as a university that might be co-sponsoring a challenge.
    The logo image file should live under static/institutionlogos/.
    """

    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
    logo_path = models.CharField(max_length=300, blank=True, null=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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
    short_name = models.CharField(max_length=16, blank=False, null=False)
    description = models.TextField(blank=True)
    form_file_path = models.CharField(max_length=300, blank=True, null=True)
    external_link = models.CharField(max_length=300, blank=True, null=True)
    type = models.CharField(max_length=50, choices=AGREEMENT_FORM_TYPE, blank=True, null=True)
    order = models.IntegerField(default=50, help_text="Indicate an order (lowest number = first listing) for how the Agreement Forms should be listed during registration workflows.")
    content = models.TextField(blank=True, null=True, help_text="If Agreement Form type is set to 'MODEL', the HTML set here will be rendered for the user")
    internal = models.BooleanField(default=False, help_text="Internal agreement forms are never presented to participants and are only submitted by administrators on behalf of participants")
    skippable = models.BooleanField(
        default=False,
        help_text="Allow participants to skip this step in instances where they have submitted the agreement form via"
                  " email or some other means. They will be required to include the name and contact information of"
                  " the person who they submitted their signed agreement form to."
    )
    template = models.CharField(max_length=300, blank=True, null=True)
    institutional_signers = models.BooleanField(default=False, help_text="Allows institutional signers to sign for their members. This will auto-approve this agreement form for members whose institutional official has had their agreement form approved.")
    form_class = models.CharField(max_length=300, null=True, blank=True)

    handler = models.CharField(max_length=512, null=True, blank=True, help_text="Set an absolute function's path to be called after the SignedAgreementForm has successfully saved")

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.name)

    def clean(self):
        if (self.type == AGREEMENT_FORM_TYPE_STATIC or not self.type) and not self.form_file_path:
            raise ValidationError("If the form type is static, the file path field should be populated.")
        if self.type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK and not self.external_link:
            raise ValidationError("If the form type is external link, the external link field should be populated.")
        if self.type == AGREEMENT_FORM_TYPE_MODEL and not self.content:
            raise ValidationError("If the form type is model, the content field should be populated with the agreement form's HTML.")
        if self.type == AGREEMENT_FORM_TYPE_FILE and not self.content and not self.form_file_path:
            raise ValidationError("If the form type is file, the content field should be populated with the agreement form's HTML.")

    def form(self, request, project, *args, **kwargs) -> "projects.forms.AgreementFormForm":

        try:
            if not self.form_class:
                return None

            # Create class from string
            components = self.form_class.rsplit(".", 1)
            module = importlib.import_module(components[0])
            form_class = getattr(module, components[1])

            # Instantiate object
            form = form_class(request, project, self, *args, **kwargs)

            return form

        except Exception as e:
            logger.exception(f"Agreement form form error: {e}", exc_info=True)

        return None

    def agreement_form_4ce_dua_status_change(self, signed_agreement_form):
        """
        This method handles status changes on signed versions of this agreement
        form.

        :param signed_agreement_form: The signed agreement form
        :type signed_agreement_form: SignedAgreementForm
        """
        logger.debug(f"[4CE-DUA]: Handling status update for SignedAgreementForm/{signed_agreement_form.id}")
        pass

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
    informational_only = models.BooleanField(default=False, blank=False, null=False, help_text="Set this to true if this project has no registration or participation steps and should only render the description panel. The Registration Open value will be ignored. The Requires Authorization flag should be set to false.")
    registration_open = models.BooleanField(default=False, blank=False, null=False, help_text="Set this to true if you want to allow users without existing permissions on this item to be able to sign up for access.")
    requires_authorization = models.BooleanField(default=True, blank=False, null=False, help_text="Set this to true if you want to explicitly require a user to have VIEW permissions on this project before they can access the project's downloads, uploads, etc.")
    automatic_authorization = models.BooleanField(default=False, blank=False, null=False, help_text="Set this to true if you want users to automatically be granted VIEW permissions on this project when they complete signup steps and request access. This is only applicable if the project is set to require authorization.")

    # Which forms users need to sign before accessing any data.
    agreement_forms = models.ManyToManyField(AgreementForm, blank=True, related_name='data_project_agreement_forms')
    shares_agreement_forms = models.BooleanField(default=False, blank=False, null=False)

    # Various tags for what a project may be, influencing where the project is listed and the functionality on its page.
    is_dataset = models.BooleanField(default=False, blank=False, null=False)
    is_challenge = models.BooleanField(default=False, blank=False, null=False)
    is_software = models.BooleanField(default=False, blank=False, null=False)

    # Set whether users need to form teams before accessing data.
    has_teams = models.BooleanField(default=False, blank=False, null=False)

    # Set whether submissions can be hosted for download or not.
    hosted_submissions = models.BooleanField(default=False, blank=False, null=False, help_text="Project administrators will be able to host user submissions for download by other users")

    # Set whether to hide incomplete shared teams or not. Incomplete means one or more participants on a shared team
    # have incomplete and/or denied DUAs or required steps.
    hide_incomplete_teams = models.BooleanField(default=False, blank=False, null=False, help_text="Shared teams that have one or more participants with incomplete project requirements will be hidden from the teams list")

    # Set whether the teams created for this project can be used by other challenges
    shares_teams = models.BooleanField(default=False, blank=False, null=False, help_text="Teams formed for this project will be automatically added to projects which use this as a team source. Teams must be approved and activated before they will be added to other projects.")
    teams_source = models.ForeignKey(
        to="DataProject",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        limit_choices_to={"shares_teams": True, "has_teams": True},
        help_text="Set this to a Data Project from which approved and activated teams should be imported for use in this Data Project. Only Data Projects that are configured to share will be available."
    )
    teams_source_message = models.TextField(default="Teams approved there will be automatically added to this project but will need still need approval for this project.", blank=True, null=True, verbose_name="Teams Source Message")

    # Set this to show badging to indicate that only commercial entities should apply for access
    commercial_only = models.BooleanField(default=False, blank=False, null=False, help_text="Commercial only projects are for commercial entities only")

    show_jwt = models.BooleanField(default=False, blank=False, null=False)

    order = models.IntegerField(blank=True, null=True, help_text="Indicate an order (lowest number = highest order) for how the DataProjects should be listed.")

    group = models.ForeignKey(
        to="Group",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text="Set this to manage where this project is shown in the navigation and interface."
    )

    # Set the optional bucket to use for storage
    bucket = models.ForeignKey(
        to="Bucket",
        on_delete=models.SET_DEFAULT,
        default=Bucket.get_default_pk,
        help_text="Set this to a specific bucket where this project's files should be stored."
    )

    # Automate approval of members covered by an already-approved institutional signer
    institutional_signers = models.BooleanField(default=False, help_text="Allows institutional signers to sign for their members. This will auto-approve agreement forms for members whose institutional official has had their agreement forms approved.")

    # Set period for automated check-ins for users with access
    data_use_report_period = models.IntegerField(blank=True, null=True, help_text="The number of days after access being granted in which emails will be sent prompting users to report on the status of their access and use of data")
    data_use_report_agreement_form = models.ForeignKey(
        to=AgreementForm,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="The agreement form that will be filled out by a user with access during periodic access and data use reporting",
    )
    data_use_report_grace_period = models.IntegerField(blank=True, null=True, help_text="The number of days in which a user is allotted to complete their access and data use reporting before their access is revoked")


    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.project_key)

    def clean(self):
        if self.informational_only and self.requires_authorization:
            raise ValidationError('Requires Authorization should be false if Informational Only is true.')

        if self.informational_only and self.is_challenge:
            raise ValidationError('Projects marked as a challenge cannot be informational only.')

        if self.is_challenge and self.is_software:
            raise ValidationError('At this time, a challenge should not also be marked as software or dataset.')

        if self.is_challenge and self.is_dataset:
            raise ValidationError('At this time, a challenge should not also be marked as software or dataset.')

        if not self.has_teams and self.shares_teams:
            raise ValidationError('A Project cannot share teams if it does not itself use teams')

        if self.teams_source and self.shares_teams:
            raise ValidationError('A Project cannot share teams if it is using shared teams from another project')


class DataProjectWorkflow(models.Model):
    """
    This represents a workflow that is associated with a DataProject.
    """

    data_project = models.ForeignKey(DataProject, on_delete=models.CASCADE, related_name='workflows')
    workflow = models.ForeignKey("workflows.Workflow", on_delete=models.CASCADE, related_name='data_project_workflows')
    requires_approval = models.BooleanField(default=False, help_text="Set this to true if this workflow requires approval before it can be marked as completed. This is used to determine if the workflow should be shown to users who have not yet been authorized for the project.")
    post_authorization = models.BooleanField(default=False, help_text="Set this to true if this workflow is intended for post-authorization dashboards. This will be used to determine if the workflow should be shown to users who have not yet been authorized for the project.")
    is_repeatable = models.BooleanField(default=False, help_text="Set this to true if this workflow can be repeated by users. This is used to determine if the workflow should be shown to users who have already completed it.")

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('data_project', 'workflow',)


class InstitutionalOfficial(models.Model):
    """
    This represents a signer that represents an institution.
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    project = models.ForeignKey(DataProject, on_delete=models.PROTECT)
    institution = models.TextField(null=False, blank=False)
    signed_agreement_form = models.ForeignKey("SignedAgreementForm", on_delete=models.PROTECT)
    member_emails = models.JSONField(null=False, blank=False, editable=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


def validate_pdf_file(value):
    """
    Ensures only a file with a content type of PDF can be persisted
    """
    if type(value.file) is UploadedFile and value.file.content_type != 'application/pdf':
        raise ValidationError('Only PDF files can be uploaded')


def signed_agreement_form_path(instance, filename):
    # file will be uploaded to PROJECTS_UPLOADS_PREFIX/<user email>_<timestamp>_<filename>
    return f'{settings.PROJECTS_UPLOADS_PREFIX}/{instance.user.email}_{datetime.now().isoformat()}_{filename}'

def signed_agreement_form_document_path(instance, filename):
    # file will be uploaded to PROJECTS_DOCUMENTS_PREFIX/<filename>
    return f'{settings.PROJECTS_DOCUMENTS_PREFIX}/{filename}'


class SignedAgreementForm(models.Model):
    """
    This represents the fully signed agreement form.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    agreement_form = models.ForeignKey(AgreementForm, on_delete=models.PROTECT)
    project = models.ForeignKey(DataProject, on_delete=models.PROTECT)
    date_signed = models.DateTimeField(auto_now_add=True)
    agreement_text = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=1, null=False, blank=False, default='P', choices=SIGNED_FORM_STATUSES)
    upload = models.FileField(null=True, blank=True, validators=[validate_pdf_file], upload_to=signed_agreement_form_path)
    fields = JSONField(null=True, blank=True)
    document = models.FileField(null=True, blank=True, upload_to=signed_agreement_form_document_path)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Signed Agreement Form'
        verbose_name_plural = 'Signed Agreement Forms'


    def get_institutional_signer_details(self) -> Optional[Tuple[str, str, list[str]]]:
        """
        Checks the SignedAgreementForm to see if it has been signed by an institutional official.
        If so, it returns the name of the institution and email of the institutional official along with a list of
        emails for the members they are representing.

        :returns: A tuple containing the institution name, official email, and a list of member emails if this is an
                  institutional signer; otherwise tuple of None, None, None
        :rtype: Optional[Tuple[str, str, list[str]]], defaults to Tuple[None, None, None]
        """
        if self.agreement_form.institutional_signers:

            # Fields should contain whether this is an institutional official or not
            if self.fields and self.fields.get("registrant_is", "").lower() == "official":

                # Ensure member emails is a list
                member_emails = self.fields.get("member_emails", [])
                if isinstance(member_emails, str):
                    member_emails = [member_emails]
                elif not isinstance(member_emails, list):
                    raise ValidationError(f"Unhandled state of 'member_emails' field: {type(member_emails)}/{member_emails}")

                # Cleanup emails to remove whitespace, if any
                member_emails = [email.strip() for email in member_emails]

                # Return values
                return self.fields["institute_name"], self.user.email, member_emails

        return None, None, None


class DataUseReportRequest(models.Model):
    """
    This model describes a request for a participant to report on data use.
    """

    participant = models.ForeignKey("Participant", on_delete=models.PROTECT)
    data_project = models.ForeignKey(DataProject, on_delete=models.CASCADE)
    signed_agreement_form = models.ForeignKey("SignedAgreementForm", null=True, blank=True, on_delete=models.PROTECT)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Data Use Report Request'
        verbose_name_plural = 'Data Use Report Requests'


class Team(models.Model):
    """
    This model describes a team of participants that are competing in a data challenge.
    """

    team_leader = models.ForeignKey(User, on_delete=models.PROTECT)
    data_project = models.ForeignKey(DataProject, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=TEAM_STATUS, default='Pending')
    source = models.ForeignKey("Team", null=True, blank=True, on_delete=models.CASCADE)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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
    permission = models.CharField(max_length=250, blank=True, null=True)

    # TODO remove or consolidate all these fields
    team_wait_on_leader_email = models.CharField(max_length=100, blank=True, null=True)
    team_wait_on_leader = models.BooleanField(default=False)
    team_pending = models.BooleanField(default=False)
    team_approved = models.BooleanField(default=False)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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
    order = models.IntegerField(blank=True, null=True, help_text="Indicate an order (lowest number = highest order) for file sets to appear within a DataProject.")

    # Set the optional bucket to use for storage
    bucket = models.ForeignKey(
        to="Bucket",
        on_delete=models.SET_DEFAULT,
        default=Bucket.get_default_pk,
        help_text="Set this to a specific bucket where this set's files are stored.",
    )

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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

    # Set the optional bucket to use for storage
    bucket = models.ForeignKey(
        to="Bucket",
        on_delete=models.SET_DEFAULT,
        default=Bucket.get_default_pk,
        help_text="Set this to a specific bucket where this file is stored.",
    )

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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

    # Optional HTML content to be displayed along with submission upload for instructions on upload preparation
    submission_instructions = models.TextField(blank=True, null=True)

    # If blank, allow infinite submissions
    max_submissions = models.IntegerField(default=1, blank=True, null=True, help_text="Leave blank if you want there to be no cap.")

    # Should the task appear on the front end (and when)
    enabled = models.BooleanField(default=False, blank=False, null=False)
    opened_time = models.DateTimeField(blank=True, null=True)
    closed_time = models.DateTimeField(blank=True, null=True)

    # Should supervisors be notified of submissions of this task
    notify_supervisors_of_submissions = models.BooleanField(default=False, blank=False, null=False, help_text="Sends a notification to any emails listed in the project's supervisors field.")

    # The content type to restrict file uploads to
    submission_file_type = models.CharField(max_length=15, default=FILE_TYPE_ZIP, choices=FILES_TYPES)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s: %s' % (self.data_project.project_key, self.title)

    def clean(self):
        if self.opened_time is not None and self.closed_time is not None and (self.opened_time > self.closed_time or self.closed_time < self.opened_time):
            raise ValidationError("Closed time must be a datetime after opened time")

    @property
    def submission_file_content_types(self):
        return FILES_CONTENT_TYPES[self.submission_file_type]


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
    file_type = models.CharField(max_length=15, default=FILE_TYPE_ZIP, choices=FILES_TYPES)

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


class Group(models.Model):
    """
    An optional grouping for projects.
    """

    key = models.CharField(max_length=100, blank=False, null=False, unique=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True)
    navigation_title = models.CharField(max_length=20, blank=True, null=True)
    parent = models.ForeignKey("Group", on_delete=models.PROTECT, blank=True, null=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def active_project_child_groups(self):
        return self.group_set.filter(dataproject__isnull=False, dataproject__visible=True).distinct()

################################################################################
# Deprecated models
################################################################################


class MIMIC3SignedAgreementFormFields(models.Model):

    signed_agreement_form = models.ForeignKey(SignedAgreementForm, on_delete=models.CASCADE)
    email = models.CharField(max_length=255)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'MIMIC3 Signed Agreement Form Fields'
        verbose_name_plural = 'MIMIC3 Signed Agreement Forms Fields'


class ROCSignedAgreementFormFields(models.Model):

    signed_agreement_form = models.ForeignKey(SignedAgreementForm, on_delete=models.CASCADE)

    # All DUAs
    day = models.CharField(max_length=2, null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)

    # N2C2-t1 ROC
    e_signature = models.CharField(max_length=255, null=True, blank=True)
    organization = models.CharField(max_length=255, null=True, blank=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'ROC signed agreement form fields'
        verbose_name_plural = 'ROC signed agreement form fields'

class DUASignedAgreementFormFields(models.Model):

    signed_agreement_form = models.ForeignKey(SignedAgreementForm, on_delete=models.CASCADE)

    # All DUAs
    day = models.CharField(max_length=2, null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)

    # N2C2-T1 DUA
    person_name = models.CharField(max_length=1024, null=True, blank=True)
    institution = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    person_phone = models.CharField(max_length=255, null=True, blank=True)
    person_email = models.CharField(max_length=255, null=True, blank=True)
    place_of_business = models.CharField(max_length=255, null=True, blank=True)
    contact_name = models.CharField(max_length=1024, null=True, blank=True)
    business_phone = models.CharField(max_length=255, null=True, blank=True)
    business_email = models.CharField(max_length=255, null=True, blank=True)
    electronic_signature = models.CharField(max_length=255, null=True, blank=True)
    professional_title = models.CharField(max_length=255, null=True, blank=True)
    date = models.CharField(max_length=255, null=True, blank=True)
    i_agree = models.CharField(max_length=10, null=True, blank=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'DUA signed agreement form fields'
        verbose_name_plural = 'DUA signed agreement form fields'

class MAYOSignedAgreementFormFields(models.Model):

    signed_agreement_form = models.ForeignKey(SignedAgreementForm, on_delete=models.CASCADE)

    # All DUAs
    day = models.CharField(max_length=2, null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)

    # Mayo DUA
    institution = models.CharField(max_length=255, null=True, blank=True)
    pi_name = models.CharField(max_length=1024, null=True, blank=True)
    i_agree = models.CharField(max_length=3, null=True, blank=True)
    recipient_institution = models.CharField(max_length=1024, null=True, blank=True)
    recipient_by = models.CharField(max_length=255, null=True, blank=True)
    recipient_its = models.CharField(max_length=255, null=True, blank=True)
    recipient_attn = models.CharField(max_length=255, null=True, blank=True)
    recipient_phone = models.CharField(max_length=255, null=True, blank=True)
    recipient_fax = models.CharField(max_length=1024, null=True, blank=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Mayo DUA signed agreement form fields'
        verbose_name_plural = 'Mayo DUA signed agreement form fields'

class NLPWHYSignedAgreementFormFields(models.Model):

    signed_agreement_form = models.ForeignKey(SignedAgreementForm, on_delete=models.CASCADE)

    # All DUAs
    day = models.CharField(max_length=2, null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)

    # NLP Research Purpose
    research_use = models.TextField(null=True, blank=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'NLP Research Purpose signed agreement form fields'
        verbose_name_plural = 'NLP Research Purpose signed agreement form fields'

class NLPDUASignedAgreementFormFields(models.Model):

    signed_agreement_form = models.ForeignKey(SignedAgreementForm, on_delete=models.CASCADE)

    # All DUAs
    day = models.CharField(max_length=2, null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)

    # NLP DUA
    form_type = models.CharField(max_length=255, null=True, blank=True)
    data_user = models.CharField(max_length=255, null=True, blank=True)
    individual_name = models.CharField(max_length=255, null=True, blank=True)
    individual_professional_title = models.CharField(max_length=255, null=True, blank=True)
    individual_address_1 = models.TextField(null=True, blank=True)
    individual_address_2 = models.TextField(null=True, blank=True)
    individual_address_city = models.CharField(max_length=255, null=True, blank=True)
    individual_address_state = models.CharField(max_length=255, null=True, blank=True)
    individual_address_zip = models.CharField(max_length=255, null=True, blank=True)
    individual_address_country = models.CharField(max_length=255, null=True, blank=True)
    individual_phone = models.CharField(max_length=255, null=True, blank=True)
    individual_fax = models.CharField(max_length=255, null=True, blank=True)
    individual_email = models.CharField(max_length=255, null=True, blank=True)
    corporation_place_of_business = models.CharField(max_length=255, null=True, blank=True)
    corporation_contact_name = models.CharField(max_length=255, null=True, blank=True)
    corporation_phone = models.CharField(max_length=255, null=True, blank=True)
    corporation_fax = models.CharField(max_length=255, null=True, blank=True)
    corporation_email = models.CharField(max_length=255, null=True, blank=True)
    research_team_person_1 = models.CharField(max_length=1024, null=True, blank=True)
    research_team_person_2 = models.CharField(max_length=1024, null=True, blank=True)
    research_team_person_3 = models.CharField(max_length=1024, null=True, blank=True)
    research_team_person_4 = models.CharField(max_length=1024, null=True, blank=True)
    data_user_signature = models.CharField(max_length=255, null=True, blank=True)
    data_user_name = models.CharField(max_length=255, null=True, blank=True)
    data_user_title = models.CharField(max_length=255, null=True, blank=True)
    data_user_address_1 = models.TextField(null=True, blank=True)
    data_user_address_2 = models.TextField(null=True, blank=True)
    data_user_address_city = models.CharField(max_length=255, null=True, blank=True)
    data_user_address_state = models.CharField(max_length=255, null=True, blank=True)
    data_user_address_zip = models.CharField(max_length=255, null=True, blank=True)
    data_user_address_country = models.CharField(max_length=255, null=True, blank=True)
    data_user_date = models.CharField(max_length=255, null=True, blank=True)
    registrant_is = models.CharField(max_length=255, null=True, blank=True)
    commercial_registrant_is = models.CharField(max_length=255, null=True, blank=True)
    data_user_acknowledge = models.CharField(max_length=3, null=True, blank=True)
    partners_name = models.CharField(max_length=255, null=True, blank=True)
    partners_title = models.CharField(max_length=255, null=True, blank=True)
    partners_address = models.TextField(null=True, blank=True)
    partners_date = models.CharField(max_length=255, null=True, blank=True)

    # Meta
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'NLP DUA signed agreement form fields'
        verbose_name_plural = 'NLP DUA signed agreement form fields'
