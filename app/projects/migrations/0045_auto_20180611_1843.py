# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-06-11 18:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0044_auto_20180611_1817'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payerdbparticipant',
            name='dua_sign_date',
            field=models.DateField(null=True),
        ),
    ]