# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-12 17:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0027_teamcomment'),
    ]

    operations = [
        migrations.AddField(
            model_name='signedagreementform',
            name='status',
            field=models.CharField(choices=[('P', 'Pending Approval'), ('A', 'Approved'), ('R', 'Rejected')], default='P', max_length=1),
        ),
    ]
