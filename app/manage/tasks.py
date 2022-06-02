import uuid
import os
import shutil
import zipfile
import requests
from django_q.tasks import Chain, async_task
from django.conf import settings
from django.contrib.auth.models import User

from projects.models import DataProject
from projects.models import ChallengeTaskSubmission
from manage.models import ChallengeTaskSubmissionExport
from dbmi_client import fileservice
from manage.api import zip_submission_file
from contact.views import email_send

import logging
logger = logging.getLogger(__name__)


def export_task_submissions(project_id, requester):
    """
    This method fetches all current submissions for a challenge task
    and prepares an export of all files along with associated metadata.
    :param project_id: The ID of the DataProject to export submissions for
    :type project_id: str
    :param requester: The email of the admin requesting the export
    :type requester: str
    :return: Whether the operation succeeded or not
    :rtype: bool
    """
    try:
        # Get project and challenge task
        project = DataProject.objects.get(id=project_id)

        # A list of file paths to each submission's zip file.
        zipped_submissions_paths = []

        # Get all submissions made by this team for this project.
        submissions = ChallengeTaskSubmission.objects.filter(
            challenge_task__in=project.challengetask_set.all(),
            deleted=False
        )

        # For each submission, create a zip file and add the path to the list of zip files.
        for submission in submissions:
            try:
                zip_file_path = zip_submission_file(submission, requester)
                zipped_submissions_paths.append(zip_file_path)
            except Exception as e:
                logger.exception(f"{project.project_key}: Could not export submission '{submission.uuid}': {e}", exc_info=True)

        # Create a directory to store the final encompassing zip file.
        final_zip_file_directory = "/tmp/" + str(uuid.uuid4())
        if not os.path.exists(final_zip_file_directory):
            os.makedirs(final_zip_file_directory)

        # Combine all the zipped tasks into one file zip file.
        final_zip_file_name = project.project_key + "__submissions.zip"
        final_zip_file_path = os.path.join(final_zip_file_directory, final_zip_file_name)
        with zipfile.ZipFile(final_zip_file_path, mode="w") as zf:
            for zip_file in zipped_submissions_paths:
                zf.write(zip_file, arcname=os.path.basename(zip_file))

        # Perform the request to upload the file
        export_uuid = export_location = None
        with open(final_zip_file_path, "rb") as file:

            # Build upload request
            files = {"file": file}
            try:
                # Create the file in Fileservice
                metadata = {
                    "project": project.project_key,
                    "type": "export",
                }
                tags = ["hypatio", "export", "submissions", project.project_key, requester]
                export_uuid, upload_data = fileservice.create_archivefile_upload(final_zip_file_name, metadata, tags)

                # Get the location
                export_location = upload_data["locationid"]

                # Upload to S3
                response = requests.post(upload_data["post"]["url"], data=upload_data["post"]["fields"], files=files)
                response.raise_for_status()

                # Mark the upload as complete
                fileservice.uploaded_archivefile(export_uuid, export_location)

            except KeyError as e:
                logger.error('Failed export post generation: {}'.format(upload_data))
                logger.exception(e)

            except requests.exceptions.HTTPError as e:
                logger.error('Failed export upload: {}'.format(upload_data))
                logger.exception(e)

        # Create the model entry for the export
        export = ChallengeTaskSubmissionExport.objects.create(
            data_project=project,
            requester=User.objects.get(email=requester),
            uuid=export_uuid,
            location=export_location,
        )

        # Set many to many fields
        export.challenge_tasks.set(project.challengetask_set.all())
        export.challenge_task_submissions.set(submissions)
        export.save()

        # Notify requester
        email_send(
            subject='DBMI Portal - Challenge Task Submissions Export',
            recipients=[requester],
            email_template='email_submissions_export_notification',
            extra={"site_url": settings.SITE_URL, "project": project}
        )

        # Delete all the directories holding the zip files.
        for path in zipped_submissions_paths:
            shutil.rmtree(os.path.dirname(os.path.realpath((path))))

        # Delete the final zip file.
        shutil.rmtree(final_zip_file_directory)

    except Exception as e:
        logger.exception(
            f"Export challange task submissions error: {e}",
            exc_info=True,
            extra={
                "project_id": project_id,
                "requester": requester,
            }
        )
