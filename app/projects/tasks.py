import uuid
import os
import shutil
import json
import requests
import tempfile
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from furl import furl

from projects.models import DataProject
from projects.models import Participant
from projects.models import DataUseReportRequest

import logging
logger = logging.getLogger(__name__)


def send_data_use_report_requests():
    """
    Runs on a daily basis and will send emails requesting data user reports be
    completed by users with access to DataProjects that have data use reporting
    requirements.
    """
    logger.debug(f"### Send Data Use Report Requests ###")

    # Iterate projects that require data use reporting
    for data_project in DataProject.objects.filter(data_use_report_agreement_form__isnull=False):
        logger.debug(f"Checking data use report requests for '{data_project.project_key}'")

        # Fetch users with access
        for participant in Participant.objects.filter(project=data_project, permission="VIEW"):
            logger.debug(f"Checking data use report requests for '{data_project.project_key}' / '{participant}'")

            # Check for existing request that is incomplete
            existing_request = DataUseReportRequest.objects.filter(data_project=data_project, participant=participant, signed_agreement_form__isnull=True).first()
            if existing_request:

                # Calculate how many days left for request
                request_delta = datetime.now(timezone.utc) - existing_request.modified
                logger.debug(f"Data use request already sent for '{data_project.project_key}' / '{participant}' {request_delta.days} ago")

                # If less than three days left, send a reminder
                if data_project.data_use_report_grace_period - request_delta.days == 3:

                    subject = '[FINAL NOTICE] DBMI Portal - Data Use Report'
                    if send_data_use_report_request(data_use_report_request=existing_request, subject=subject, days_left=3):
                        logger.debug(f"Data use request reminder sent for '{data_project.project_key}' / '{participant}'")
                    else:
                        logger.error(f"Data use report request reminder not sent")

                elif data_project.data_use_report_grace_period - request_delta.days < 0:

                    # Revoke access
                    logger.debug(f"Data use request not heeded '{data_project.project_key}' / '{participant}', revoking access")
                    participant.permission = None
                    participant.save()

            else:
                # Create the request
                data_use_report_request = DataUseReportRequest.objects.create(data_project=data_project, participant=participant)

                # Get access granted date and compare it to report period
                access_delta = datetime.now(timezone.utc) - participant.modified
                if access_delta.days >= data_project.data_use_report_period:

                    subject = '[ACTION REQUIRED] DBMI Portal - Data Use Report'
                    if send_data_use_report_request(data_use_report_request=data_use_report_request, subject=subject):
                        logger.debug(f"Data use request sent for '{data_project.project_key}' / '{participant}'")
                    else:
                        logger.error(f"Data use report request not sent")


def send_data_use_report_request(data_use_report_request, subject='[ACTION REQUIRED] DBMI Portal - Data Use Report', days_left=None):

    try:
        # Form the context.
        data_use_report_url = furl(settings.SITE_URL) / reverse("projects:data_use_report", kwargs={"request_id": data_use_report_request.id})

        # If not passed, use the grace period for number of days left to comply
        if not days_left:
            days_left = data_use_report_request.data_project.data_use_report_grace_period

        context = {
            'project': data_use_report_request.data_project,
            'data_use_report_url': data_use_report_url.url,
            'grace_period_days': days_left,
        }

        # Render templates
        body_html = render_to_string('email/email_data_use_report.html', context)
        body = render_to_string('email/email_data_use_report.txt', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_FROM_ADDRESS,
            reply_to=(settings.EMAIL_REPLY_TO_ADDRESS, ),
            to=[data_use_report_request.participant.user.email]
        )
        email.attach_alternative(body_html, "text/html")
        email.send()

        return True

    except Exception as e:
        logger.exception(f"Error sending request: {e}", exc_info=True)
        return False
