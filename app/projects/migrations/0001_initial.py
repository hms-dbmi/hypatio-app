# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-01-26 19:34
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import projects.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AgreementForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('form_html', models.FileField(upload_to=projects.models.get_agreement_form_upload_path)),
            ],
        ),
        migrations.CreateModel(
            name='DataProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True, unique=True, verbose_name='Name of project')),
                ('project_key', models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Project Key')),
                ('institution', models.CharField(blank=True, max_length=255, null=True, verbose_name='Institution')),
                ('description', models.CharField(blank=True, max_length=4000, null=True, verbose_name='Description')),
                ('short_description', models.CharField(blank=True, max_length=255, null=True, verbose_name='Short Description')),
                ('permission_scheme', models.CharField(default='PRIVATE', max_length=100, verbose_name='Permission Scheme')),
                ('agreement_forms_required', models.BooleanField(default=True)),
                ('project_supervisor', models.CharField(blank=True, max_length=255, null=True, verbose_name='Project Supervisor')),
                ('is_contest', models.BooleanField(default=False)),
                ('agreement_forms', models.ManyToManyField(blank=True, related_name='data_project_agreement_forms', to='projects.AgreementForm')),
            ],
        ),
        migrations.CreateModel(
            name='SignedAgreementForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_signed', models.DateTimeField(auto_now_add=True)),
                ('agreement_text', models.TextField()),
                ('agreement_form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.AgreementForm')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
