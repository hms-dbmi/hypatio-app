from django.db import models

from .models import ParticipantProject
from .models import SignedAgreementForm
from .models import Participant

from django.contrib.auth.models import User


class PayerDBForm(SignedAgreementForm):
    name = models.CharField(max_length=255, blank=False, null=True, verbose_name="Your name")
    title = models.CharField(max_length=100, blank=False, null=True, verbose_name="Your title")
    harvard_address = models.CharField(max_length=255, blank=False, null=True, verbose_name="Harvard Address")
    phone = models.CharField(max_length=255, blank=False, null=True, verbose_name="Phone Number")
    primary_department = models.CharField(max_length=255, blank=False, null=True, verbose_name="Primary Harvard Department")
    specific_aims = models.TextField(blank=False, null=True, verbose_name="Please provide a concise 'specific aims page style description of the proposed work")
    number_team_access = models.CharField(max_length=255, blank=False, null=True, verbose_name="Approximately how many team members will require access to the HDS database?")
    team_sql = models.CharField(max_length=255, blank=False, null=True, verbose_name="Are the team members familiar with relational databases and the SQL programming language?")
    team_r = models.CharField(max_length=255, blank=False, null=True, verbose_name="Are the team members familiar with the R programming environment?")
    team_orchestra = models.CharField(max_length=255, blank=False, null=True, verbose_name="Are the team members familiar with HMS’ Orchestra cluster computing environment?")
    team_windows = models.CharField(max_length=255, blank=False, null=True, verbose_name="Are the team members familiar with the Windows Server "
                                         "environment and if so, do they have experience working "
                                         "remotely on a Windows platform using Remote Desktop?")
    team_analysis = models.CharField(max_length=255, blank=False, null=True, verbose_name="What is your team’s preferred analysis platform (list all that"
                                          " apply, e.g., R, Matlab, Python, SAS)?")
    team_interests = models.CharField(max_length=255, blank=False, null=True, verbose_name="Please briefly list the primary research interests of "
                                           "your team (e.g., “healthcare economics”, “viral epidemiology”, etc.)")
    funding = models.CharField(max_length=255, blank=False, null=True, verbose_name="Please list any relevant funding sources for this work")
    protocol_number = models.CharField(max_length=255, blank=True, null=True, verbose_name="Do you have an existing IRB protocol that covers the "
                                            "proposed work? If so, please provide the protocol number "
                                            "and a copy of the approved proposal.")
    signature = models.CharField(max_length=255, blank=False, null=True, verbose_name="By signing this form, I acknowledge that I have read "
                                      "and agreed to the following terms of use, and will abide by "
                                      "them during the study period.")


class PayerDBParticipant(Participant):
    # Admin facing fields.
    dua_signed = models.BooleanField(default=False)
    dua_sign_date = models.DateField()

    access_status = models.CharField(max_length=255, blank=False, null=True, verbose_name="Access Status")
    ecommons_id = models.CharField(max_length=255, blank=False, null=True, verbose_name="eCommons")
    ip_address = models.CharField(max_length=255, blank=False, null=True, verbose_name="IP Address")


class PayerDBProject(ParticipantProject):

    funding_status = models.CharField(max_length=250)

    def __str__(self):
        return '%s' % (self.uuid)