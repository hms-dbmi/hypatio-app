# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-06-21 17:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0046_auto_20180611_1846'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataproject',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Name of project'),
        ),
    ]
