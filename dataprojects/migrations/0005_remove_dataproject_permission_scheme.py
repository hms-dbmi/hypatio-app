# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-05-09 23:46
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dataprojects', '0004_dataproject_project_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataproject',
            name='permission_scheme',
        ),
    ]
