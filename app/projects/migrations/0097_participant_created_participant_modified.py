# Generated by Django 4.1.6 on 2023-02-14 17:07

from django.db import migrations, models

from projects.models import Participant, SignedAgreementForm


def migrate_participants_model(apps, schema_editor):
    """
    Attempts to set a roughly accurate date of when each object would have
    been created. This is calculated by fetching the date of the last
    signed SignedAgreementForm relevant to the DataProjects.
    """
    # Do nothing due to issue with Django accessing properties not added
    # until later migration
    # This migration was moved to 0100
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0096_participant_created_participant_modified'),
    ]

    operations = [
        migrations.RunPython(migrate_participants_model),
    ]
