# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-02-02 14:41
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_auto_20180202_1439'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teammemberstatus',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.Team'),
        ),
    ]
