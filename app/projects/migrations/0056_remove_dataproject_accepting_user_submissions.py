# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-17 13:57
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0055_auto_20180814_1538'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataproject',
            name='accepting_user_submissions',
        ),
    ]