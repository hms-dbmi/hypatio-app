import sys
import tempfile
import requests
import shutil
import boto3
import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from dbmi_client import fileservice

from projects.models import DataProject
from projects.models import SignedAgreementForm
from projects.models import AgreementForm

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Export signed agreement forms'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('project_key', type=str)
        parser.add_argument('agreement_form', type=str)
        parser.add_argument('status', type=str, default='A')

    def handle(self, *args, **options):

        # Ensure it exists
        if not DataProject.objects.filter(project_key=options['project_key']).exists():
            raise CommandError(f'Project with key "{options["project_key"]}" does not exist')
        if not AgreementForm.objects.filter(short_name=options['agreement_form']).exists():
            raise CommandError(f'Agreement Form with name "{options["agreement_form"]}" does not exist')

        # Get the objects
        project = DataProject.objects.get(project_key=options['project_key'])
        agreement_form = AgreementForm.objects.get(short_name=options['agreement_form'])
        signed_agreement_forms = SignedAgreementForm.objects.filter(
            project=project,
            agreement_form=agreement_form,
            status=options["status"],
        )

        # Ensure we've got Qualtrics surveys
        if not signed_agreement_forms:
            self.stdout.write(
                f'{project.project_key}/{agreement_form.name}: Does not have any signed agreement forms'
            )
            return

        export_uuid = export_location = export_url = None
        try:
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as directory:

                # Set the archive name
                archive_root = os.path.join(directory, "signed_agreement_forms")
                os.makedirs(archive_root)
                archive_basename = f"{project.project_key}_{agreement_form.short_name}"

                # Create boto client
                s3 = boto3.client("s3")

                # Download DUAs
                for signed_agreement_form in signed_agreement_forms:

                    try:
                        # Set the key
                        key = os.path.join(settings.PROJECTS_UPLOADS_PREFIX, signed_agreement_form.upload.name)

                        # Download the file
                        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, key, os.path.join(archive_root, signed_agreement_form.upload.name))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error: Could not download signed agreement form file: {e}"
                        ))

                # Archive the directory
                archive_path = shutil.make_archive(archive_basename, "zip", archive_root)
                logger.debug(f"Export archive: {archive_path}")

                # Perform the request to upload the file
                with open(archive_path, "rb") as file:

                    # Build upload request
                    response = None
                    files = {"file": file}
                    try:
                        # Create the file in Fileservice
                        metadata = {
                            "project": project.project_key,
                            "agreement_form": agreement_form.short_name,
                            "type": "export",
                        }
                        tags = ["hypatio", "export", "signed-agreement-forms", project.project_key, ]
                        export_uuid, upload_data = fileservice.create_archivefile_upload(os.path.basename(archive_path), metadata, tags)

                        # Get the location
                        export_location = upload_data["locationid"]

                        # Upload to S3
                        response = requests.post(upload_data["post"]["url"], data=upload_data["post"]["fields"], files=files)
                        response.raise_for_status()

                        # Mark the upload as complete
                        fileservice.uploaded_archivefile(export_uuid, export_location)

                        # Get the download URL
                        export_url = fileservice.get_archivefile_download_url(export_uuid)

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

            # Return export UUID
            self.stdout.write(f"Export: {export_url}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Error: {e}"
            ))
            sys.exit(1)
