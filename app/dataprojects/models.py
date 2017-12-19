from django.db import models
from django.contrib.auth.models import User

class DataProject(models.Model):
    """
    This represents a data project that users can access, along with its permissions and requirements.
    """
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of project", unique=True)
    institution = models.CharField(max_length=255, blank=True, null=True, verbose_name="Institution")
    description = models.CharField(max_length=4000, blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")
    project_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Project Key", unique=True)
    project_url = models.CharField(max_length=255, blank=True, null=True, verbose_name="Project URL")
    permission_scheme = models.CharField(max_length=100, default="PRIVATE", verbose_name="Permission Scheme")
    dua_required = models.BooleanField(default=True)
    project_supervisor = models.CharField(max_length=255, blank=True, null=True, verbose_name="Project Supervisor")

    def __str__(self):
        return '%s %s' % (self.project_key, self.name)

class DataUseAgreement(models.Model):
    """
    This represents a DUA that a user might need to sign to acquire access to a data project. This model points
    to an HTML file in our static/dua_forms folder containing the DUA.
    """
    name = models.CharField(max_length=100, blank=False, null=False, verbose_name="name")
    project = models.ForeignKey(DataProject, related_name='duas')
    agreement_form_file = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return '%s - %s' % (self.name, self.project.project_key)

class DataUseAgreementSign(models.Model):
    """
    This represents a user signing a DUA for a specific project.
    """
    data_use_agreement = models.ForeignKey(DataUseAgreement)
    user = models.ForeignKey(User)
    date_signed = models.DateTimeField(auto_now_add=True)
    agreement_text = models.TextField(blank=False)

    def __str__(self):
        return '%s %s' % (self.data_use_agreement.name, self.user.email)