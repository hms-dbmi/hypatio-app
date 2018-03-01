import boto3
import requests
from botocore.client import Config
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def _s3_client():
    # Get the service client with sigv4 configured
    return boto3.client('s3',
                        aws_access_key_id=settings.S3_AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.S3_AWS_SECRET_ACCESS_KEY,
                        config=Config(signature_version='s3v4'))


def get_download_url(file_name, expires_in=3600):
    logger.debug('[file_services][get_download_url] Generating URL for {}'.format(file_name))

    # Generate the URL to get the file object
    url = _s3_client().generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': settings.S3_BUCKET,
            'Key': file_name
        },
        ExpiresIn=expires_in
    )

    logger.debug('[file_services][get_download_url] Generated URL: {}'.format(url))

    return url


def upload_file(file_name, file, expires_in=3600):
    logger.error('[file_services][upload_file] Uploading file: {}'.format(file_name))

    # Generate the POST attributes
    post = _s3_client().generate_presigned_post(
        Bucket=settings.S3_BUCKET,
        Key=file_name,
        ExpiresIn=expires_in
    )

    # Perform the request to upload the file
    files = {"file": file}
    try:
        response = requests.post(post["url"], data=post["fields"], files=files)
        response.raise_for_status()

        return response

    except KeyError as e:
        logger.error('[file_services][upload_file] Failed post generation: {}'.format(post))
        logger.exception(e)

    except requests.exceptions.HTTPError as e:
        logger.error('[file_services][upload_file] Failed upload: {}'.format(post))
        logger.exception(e)

