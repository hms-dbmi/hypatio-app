# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-02-02 14:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_auto_20180202_1441'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='teammemberstatus',
            name='participant',
        ),
        migrations.RemoveField(
            model_name='teammemberstatus',
            name='team',
        ),
        migrations.AddField(
            model_name='participant',
            name='team_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='participant',
            name='team_pending',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='participant',
            name='team_wait_on_pi',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='participant',
            name='team_wait_on_pi_email',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.DeleteModel(
            name='TeamMemberStatus',
        ),
    ]
