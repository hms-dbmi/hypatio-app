# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-16 14:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0028_signedagreementform_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParticipantSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('file', models.FileField(upload_to='')),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Participant')),
            ],
        ),
    ]
