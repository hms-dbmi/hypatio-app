# Generated by Django 2.2.28 on 2022-06-02 14:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0092_auto_20220517_1520'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChallengeTaskSubmissionExport',
            fields=[
                ('request_date', models.DateTimeField(auto_now_add=True)),
                ('uuid', models.UUIDField(default=None, primary_key=True, serialize=False, unique=True)),
                ('location', models.CharField(blank=True, default=None, max_length=12, null=True)),
                ('challenge_task_submissions', models.ManyToManyField(to='projects.ChallengeTaskSubmission')),
                ('challenge_tasks', models.ManyToManyField(to='projects.ChallengeTask')),
                ('data_project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='projects.DataProject')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]