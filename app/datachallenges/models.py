from django.db import models
from django.contrib.auth.models import User

class DataChallenge(models.Model):
    """
    This represents a data challenge that users can access, along with its permissions and requirements.
    """
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of Challenge", unique=True)
    institution = models.CharField(max_length=255, blank=True, null=True, verbose_name="Institution")
    description = models.CharField(max_length=4000, blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")
    challenge_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Challenge Key", unique=True)
    permission_scheme = models.CharField(max_length=100, default="PRIVATE", verbose_name="Permission Scheme")
    dua_required = models.BooleanField(default=True)
    challenge_supervisor = models.CharField(max_length=255, blank=True, null=True, verbose_name="Challenge Supervisor")

    def __str__(self):
        return '%s %s' % (self.challenge_key, self.name)
