# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-06-21 14:06
from __future__ import unicode_literals

from django.db import migrations

# Now that we've added is_dataset as a new flag on a DataProject, we will want to set
# all existing DataProjects that are not challenges as datasets.
def tag_as_dataset_if_not_a_challenge(apps, schema_editor):
    DataProject = apps.get_model('projects', 'DataProject')
    for project in DataProject.objects.all():
        if not project.is_challenge:
            project.is_dataset = True
            project.save()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0076_auto_20190621_1401'),
    ]

    operations = [
        migrations.RunPython(tag_as_dataset_if_not_a_challenge),
    ]
