# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-08 21:07
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0014_auto_20180208_2107'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dataproject',
            old_name='project_visible',
            new_name='visible',
        ),
    ]