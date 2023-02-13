import uuid
import os
import shutil
import json
import requests
import tempfile
from datetime import datetime
from django_q.tasks import Chain, async_task
from django.conf import settings
from django.contrib.auth.models import User

from projects.models import DataProject
from projects.models import ChallengeTaskSubmission
from projects.models import ChallengeTaskSubmissionDownload
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

        # Get all submissions made by this team for this project.
        submissions = ChallengeTaskSubmission.objects.filter(
            challenge_task__in=project.challengetask_set.all(),
            deleted=False
        )

        # Create a temporary directory
        export_uuid = export_location = None
        with tempfile.TemporaryDirectory() as directory:

            # Create directory to put submissions in
            submissions_directory_path = os.path.join(directory, f"{project.project_key}_submissions_{datetime.now().isoformat()}")

            # For each submission, create a directory for the file and its metadata file
            submission_file_response = None
            for submission in submissions:
                try:
                    # Set the name of the containing directory
                    submission_directory_path = os.path.join(submissions_directory_path, f"{submission.participant.user.email}_{submission.uuid}")

                    # Create a record of the user downloading the file.
                    ChallengeTaskSubmissionDownload.objects.create(
                        user=User.objects.get(email=requester),
                        submission=submission
                    )

                    # Create a temporary directory to hold the files specific to this submission that need to be zipped together.
                    if not os.path.exists(submission_directory_path):
                        os.makedirs(submission_directory_path)

                    # Create a json file with the submission info string.
                    info_file_name = "submission_info.json"
                    with open(os.path.join(submission_directory_path, info_file_name), mode="w") as f:
                        f.write(submission.submission_info)

                    # Determine filename
                    try:
                        submission_file_name = json.loads(submission.submission_info).get("filename")
                        if not submission_file_name:

                            # Check fileservice
                            submission_file_name = fileservice.get_archivefile(submission.uuid)["filename"]
                    except Exception as e:
                        logger.exception(
                            f"Could not determine filename for submission",
                            exc_info=True,
                            extra={
                                "submission": submission,
                                "archivefile_uuid": submission.uuid,
                                "submission_info": submission.submission_info,
                            }
                        )

                        # Use a default filename
                        submission_file_name = "submission_file.zip"

                    # Get the submission file's byte contents from S3.
                    submission_file_download_url = fileservice.get_archivefile_proxy_url(uuid=submission.uuid)
                    headers = {"Authorization": f"{settings.FILESERVICE_AUTH_HEADER_PREFIX} {settings.FILESERVICE_SERVICE_TOKEN}"}
                    with requests.get(submission_file_download_url, headers=headers, stream=True) as submission_file_response:
                        submission_file_response.raise_for_status()

                        # Write the submission file's bytes to a zip file.
                        with open(os.path.join(submission_directory_path, submission_file_name), mode="wb") as f:
                            shutil.copyfileobj(submission_file_response.raw, f)

                except requests.exceptions.HTTPError as e:
                    logger.exception(
                        f"{project.project_key}: Could not download submission '{submission.uuid}': {e}",
                        extra={
                            "submission": submission,
                            "archivefile_uuid": submission.uuid,
                            "response": submission_file_response.content,
                            "status_code": submission_file_response.status_code
                        })

                except Exception as e:
                    logger.exception(
                        f"{project.project_key}: Could not export submission '{submission.uuid}': {e}",
                        exc_info=True
                    )

            # Set the archive name
            archive_basename = f"{project.project_key}_submissions"

            # Archive the directory
            archive_path = shutil.make_archive(archive_basename, "zip", submissions_directory_path)

            # Perform the request to upload the file
            with open(archive_path, "rb") as file:

                # Build upload request
                response = None
                files = {"file": file}
                try:
                    # Create the file in Fileservice
                    metadata = {
                        "project": project.project_key,
                        "type": "export",
                    }
                    tags = ["hypatio", "export", "submissions", project.project_key, requester]
                    export_uuid, upload_data = fileservice.create_archivefile_upload(os.path.basename(archive_path), metadata, tags)

                    # Get the location
                    export_location = upload_data["locationid"]

                    # Upload to S3
                    response = requests.post(upload_data["post"]["url"], data=upload_data["post"]["fields"], files=files)
                    response.raise_for_status()

                    # Mark the upload as complete
                    fileservice.uploaded_archivefile(export_uuid, export_location)

                except KeyError as e:
                    logger.error(
                        f'{project.project_key}: Failed export post generation: {upload_data}',
                        exc_info=True
                    )
                    raise e

                except requests.exceptions.HTTPError as e:
                    logger.exception(
                        f'{project.project_key}: Failed export upload: {upload_data}',
                        extra={
                            "response": response.content,
                            "status_code": response.status_code
                        }
                    )
                    raise e

                except Exception as e:
                    logger.exception(
                        f"{project.project_key}: Could not export submissions: {e}",
                        exc_info=True,
                    )
                    raise e

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

    except Exception as e:
        logger.exception(
            f"Export challenge task submissions error: {e}",
            exc_info=True,
            extra={
                "project_id": project_id,
                "requester": requester,
            }
        )
        raise e
