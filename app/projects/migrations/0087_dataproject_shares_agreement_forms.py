# Generated by Django 2.2.25 on 2021-12-17 23:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0086_auto_20211212_1445'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataproject',
            name='shares_agreement_forms',
            field=models.BooleanField(default=False),
        ),
    ]