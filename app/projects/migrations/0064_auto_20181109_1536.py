# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-09 15:36
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0063_auto_20181109_1530'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dataproject',
            old_name='require_authorization',
            new_name='requires_authorization',
        ),
    ]
