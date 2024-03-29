# Generated by Django 2.2.28 on 2022-05-17 15:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0091_auto_20220512_2129'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataproject',
            name='hide_incomplete_teams',
            field=models.BooleanField(default=False, help_text='Shared teams that have one or more participants with incomplete project requirements will be hidden from the teams list'),
        ),
        migrations.AddField(
            model_name='dataproject',
            name='hosted_submissions',
            field=models.BooleanField(default=False, help_text='Project administrators will be able to host user submissions for download by other users'),
        ),
        migrations.AlterField(
            model_name='dataproject',
            name='shares_teams',
            field=models.BooleanField(default=False, help_text='Teams formed for this project will be automatically added to projects which use this as a team source. Teams must be approved and activated before they will be added to other projects.'),
        ),
        migrations.AlterField(
            model_name='dataproject',
            name='teams_source',
            field=models.ForeignKey(blank=True, help_text='Set this to a Data Project from which approved and activated teams should be imported for use in this Data Project. Only Data Projects that are configured to share will be available.', limit_choices_to={'has_teams': True, 'shares_teams': True}, null=True, on_delete=django.db.models.deletion.PROTECT, to='projects.DataProject'),
        ),
    ]
