# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-13 20:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0052_auto_20180813_1928'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataprojectsubmission',
            name='submission_form_file_path',
        ),
        migrations.AddField(
            model_name='dataprojectsubmission',
            name='dataprojectsubmissiontype',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='projects.DataProjectSubmissionType'),
            preserve_default=False,
        ),
    ]