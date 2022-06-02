import logging
import os
import shutil
import uuid
import zipfile
import requests
from django.contrib.auth.models import User
from dbmi_client import fileservice

from hypatio import file_services
from projects.models import ChallengeTaskSubmissionDownload

# Get an instance of a logger
logger = logging.getLogger(__name__)


def zip_submission_file(submission, requester, request=None):
    """
    Creates a zip file containing a ChallengeTaskSubmission's file and the info json. The
    submission file is pulled from fileservice.

    :param submission: The submission object to zip
    :type submission: ChallengeTaskSubmission
    :param requester: The email of the admin requesting the export
    :type requester: str
    :param request: The current request, if any
    :type: request: HttpRequest
    :returns: Returns the path to the zip file.
    :rtype: str
    """

    # Create a record of the user downloading the file.
    ChallengeTaskSubmissionDownload.objects.create(
        user=User.objects.get(email=requester),
        submission=submission
    )

    # Create a temporary directory to hold the files specific to this submission that need to be zipped together.
    working_directory = "/tmp/" + str(uuid.uuid4())
    if not os.path.exists(working_directory):
        os.makedirs(working_directory)

    # Create a json file with the submission info string.
    info_file_name = "submission_info.json"
    with open(working_directory + "/" + info_file_name, mode="w") as f:
        f.write(submission.submission_info)

    # Get the submission file's byte contents from S3.
    submission_file_download_url = fileservice.get_archivefile_download_url(uuid=submission.uuid)
    submission_file_request = requests.get(submission_file_download_url)

    # Write the submission file's bytes to a zip file.
    submission_file_name = "submission_file.zip"
    if submission_file_request.status_code == 200:
        with open(working_directory + "/" + submission_file_name, mode="wb") as f:
            f.write(submission_file_request.content)
    else:
        raise Exception("Participant submission {uuid} file could not be pulled from S3.".format(uuid=submission.uuid))

    # Create a temporary directory to hold the final zip file. Isolates the file to prevent any overlaps.
    zip_file_directory = "/tmp/" + str(uuid.uuid4())
    if not os.path.exists(zip_file_directory):
        os.makedirs(zip_file_directory)

    zip_file_name = "{project}__{task}__{person}__{uuid}.zip".format(
        project=submission.challenge_task.data_project.project_key,
        task=submission.challenge_task.title,
        person=submission.participant.user.email,
        uuid=submission.uuid
    )

    zip_file_path = "{directory}/{zip_file_name}".format(
        directory=zip_file_directory,
        zip_file_name=zip_file_name
    )

    # Zip up the files.
    with zipfile.ZipFile(zip_file_path, mode="w") as zf:
        zf.write(working_directory + "/" + info_file_name, arcname=info_file_name)
        zf.write(working_directory + "/" + submission_file_name, arcname=submission_file_name)

    # Delete the working directory.
    shutil.rmtree(working_directory)

    # Return the path to the zip file.
    return zip_file_path
