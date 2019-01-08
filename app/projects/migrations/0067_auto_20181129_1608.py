# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-29 16:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0066_auto_20181128_1623'),
    ]

    operations = [
        migrations.AddField(
            model_name='challengetask',
            name='notify_admins_of_submissions',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='challengetask',
            name='max_submissions',
            field=models.IntegerField(blank=True, default=1, help_text='Leave blank if you want there to be no cap.', null=True),
        ),
    ]