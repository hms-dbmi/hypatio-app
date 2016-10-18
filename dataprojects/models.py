from django.db import models

class DataProject(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name of project")
    institution = models.CharField(max_length=255, blank=True, null=True, verbose_name="Institution")
    description = models.CharField(max_length=4000, blank=True, null=True, verbose_name="Description")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")

