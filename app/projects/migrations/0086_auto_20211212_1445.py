# Generated by Django 2.2.25 on 2021-12-12 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0085_auto_20211210_1743'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataproject',
            name='shares_teams',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='dataproject',
            name='teams_source',
            field=models.ForeignKey(blank=True, help_text='Set this to a Data Project from which teams should be imported for use in this Data Project. Only Data Projects that are configured to share will be available.', limit_choices_to={'has_teams': True, 'shares_teams': True}, null=True, on_delete=django.db.models.deletion.PROTECT, to='projects.DataProject'),
        ),
        migrations.AddField(
            model_name='team',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.Team'),
        ),
    ]