# Generated by Django 2.2.24 on 2021-11-30 21:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0079_duasignedagreementformfields_mayosignedagreementformfields_nlpduasignedagreementformfields_nlpwhysig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agreementform',
            name='short_name',
            field=models.CharField(max_length=16),
        ),
    ]
