import logging
from django.conf import settings
from contact.views import email_send
from projects.models import ChallengeTaskSubmission

logger = logging.getLogger(__name__)

def notify_task_submitters(project, participant, task, submission_info_json):
    """
    Sends an email notification to individuals involved in a submission, which may be a single
    person or a group of people under a team.
    """

    # Send an email notification to the team or individual who submitted.
    if project.has_teams:

        # Get the submissions for this task already submitted by the team.
        total_submissions = ChallengeTaskSubmission.objects.filter(
            challenge_task=task,
            participant__in=participant.team.participant_set.all(),
            deleted=False
        ).count()

        # Send an email notification to team members about the submission.
        emails = [member.user.email for member in participant.team.participant_set.all()]

        # The email subject.
        subject = 'DBMI Portal - {project} solution submitted by your team'.format(project=project.project_key)

    else:
        # Get the submissions for this task already submitted by the team.
        total_submissions = ChallengeTaskSubmission.objects.filter(
            challenge_task=task,
            participant=participant,
            deleted=False
        ).count()

        # Send an email notification to team members about the submission.
        emails = [participant.user.email]

        # The email subject.
        subject = 'DBMI Portal - {project} solution submitted.'.format(project=project.project_key)

    context = {
        'submission_info': submission_info_json,
        'project': project,
        'task': task,
        'submitter': participant.user.email,
        'max_submissions': task.max_submissions,
        'submission_count': total_submissions
    }

    try:
        email_success = email_send(
            subject=subject,
            recipients=emails,
            email_template='email_submission_uploaded',
            extra=context
        )
    except Exception as e:
        logger.exception(e)

def notify_supervisors_of_task_submission(project, participant, task, submission_info_json):
    """
    Sends an email notification to supervisors of a data project when someone
    has submitted a task.
    """

    # Convert the comma separated string of emails into a list.
    supervisor_emails = project.project_supervisors.split(",")

    # The email subject.
    subject = 'DBMI Portal - A {project} solution was submitted.'.format(project=project.project_key)

    context = {
        'submission_info': submission_info_json,
        'project': project,
        'task': task,
        'submitter': participant.user.email,
        'site_url': settings.SITE_URL
    }

    try:
        email_success = email_send(
            subject=subject,
            recipients=supervisor_emails,
            email_template='email_submission_uploaded_to_supervisors',
            extra=context
        )
    except Exception as e:
        logger.exception(e)
