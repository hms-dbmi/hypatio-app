from django.db import models


class DataProject(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of project")
    institution = models.CharField(max_length=255, blank=True, null=True, verbose_name="Institution")
    description = models.CharField(max_length=4000, blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")
    project_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Project Key")
    permission_scheme = models.CharField(max_length=100, blank=True, null=True, verbose_name="Permission Scheme")
    project_url = models.CharField(max_length=255, blank=True, null=True, verbose_name="Project URL")
