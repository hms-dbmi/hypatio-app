# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-09 14:12
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import projects.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_auto_20180206_2021'),
    ]

    operations = [
        migrations.RenameField(
            model_name='participant',
            old_name='team_wait_on_pi',
            new_name='team_wait_on_leader',
        ),
        migrations.RenameField(
            model_name='participant',
            old_name='team_wait_on_pi_email',
            new_name='team_wait_on_leader_email',
        ),
        migrations.RenameField(
            model_name='team',
            old_name='principal_investigator',
            new_name='team_leader',
        ),
        migrations.AlterField(
            model_name='agreementform',
            name='form_html',
            field=models.FileField(upload_to=projects.models.get_agreement_form_upload_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['html'])]),
        ),
    ]
