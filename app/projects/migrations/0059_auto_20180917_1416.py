# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-17 14:16
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0058_auto_20180821_1754'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dataproject',
            old_name='is_contest',
            new_name='is_challenge',
        ),
    ]