# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-13 19:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0050_auto_20180713_1346'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataProjectSubmissionType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default=None, max_length=200)),
                ('description', models.CharField(blank=True, max_length=2000, null=True)),
                ('max_submissions', models.IntegerField(default=1)),
                ('opened_time', models.DateTimeField(blank=True, null=True)),
                ('closed_time', models.DateTimeField(blank=True, null=True)),
                ('enabled', models.BooleanField(default=False)),
                ('data_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.DataProject')),
            ],
        ),
        migrations.RenameModel(
            old_name='ParticipantSubmission',
            new_name='DataProjectSubmission',
        ),
    ]
