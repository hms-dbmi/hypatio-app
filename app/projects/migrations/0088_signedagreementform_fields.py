# Generated by Django 2.2.26 on 2022-01-31 20:35

from django.db import migrations
import django_jsonfield_backport.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0087_dataproject_shares_agreement_forms'),
    ]

    operations = [
        migrations.AddField(
            model_name='signedagreementform',
            name='fields',
            field=django_jsonfield_backport.models.JSONField(blank=True, null=True),
        ),
    ]
