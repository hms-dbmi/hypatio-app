import boto3
import requests
import furl
from botocore.client import Config
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def build_url(base, path):

    # Start with the base.
    url = furl.furl(base)

    # Get current segments, leaving out blanks
    segments = list(filter(None, url.path.segments))

    # Split the path, leaving out blanks
    segments.extend(list(filter(None, path.split('/'))))

    # Add a trailing item to ensure we have a trailing slash
    segments.append('')

    url.path.segments = segments

    return url.url


def headers(request):

    # Find the JWT.
    token = request.META.get('HTTP_AUTHORIZATION', 'SERVICE {}'.format(settings.FILESERVICE_SERVICE_TOKEN))

    return {"Authorization": token,
            'Content-Type': 'application/json'}


def get(request, path, params=None):
    logger.debug('Path: {}'.format(path))

    try:
        # Build the url.
        url = build_url(settings.FILESERVICE_API_URL, path)

        # Prepare the request.
        response = requests.get(url, headers=headers(request), params=params)

        logger.debug('URL: {}, Response: {}'.format(url, response.status_code))

        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.exception('Exception: {}'.format(e))

    return None


def post(request, path, data):
    logger.debug('Path: {}'.format(path))

    # Build the url.
    url = build_url(settings.FILESERVICE_API_URL, path)

    try:
        # Prepare the request.
        response = requests.post(url, headers=headers(request), json=data)

        logger.debug('URL: {}, Response: {}'.format(url, response.status_code))

        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.exception('Exception: {}'.format(e))

    return None


def put(request, path, data):
    logger.debug('Path: {}'.format(path))

    # Build the url.
    url = build_url(settings.FILESERVICE_API_URL, path)

    try:

        # Prepare the request.
        response = requests.put(url, headers=headers(request), json=data)

        logger.debug('URL: {}, Response: {}'.format(url, response.status_code))

        response.raise_for_status()

        return response

    except Exception as e:
        logger.exception('Exception: {}'.format(e))

    return False


def patch(request, path, data):
    logger.debug('Path: {}'.format(path))

    # Build the url.
    url = build_url(settings.FILESERVICE_API_URL, path)

    try:

        # Prepare the request.
        response = requests.patch(url, headers=headers(request), json=data)

        logger.debug('URL: {}, Response: {}'.format(url, response.status_code))

        response.raise_for_status()

        return response

    except Exception as e:
        logger.exception('Exception: {}'.format(e))

    return False


def delete(request, path, params=None):
    logger.debug('Path: {}'.format(path))

    # Build the url.
    url = build_url(settings.FILESERVICE_API_URL, path)

    try:

        # Prepare the request.
        response = requests.delete(url, headers=headers(request), params=params)

        logger.debug('URL: {}, Response: {}'.format(url, response.status_code))

        response.raise_for_status()

        return response

    except Exception as e:
        logger.exception('Exception: {}'.format(e))

    return False


def check_groups(request):

    # Get current groups.
    groups = get(request, 'groups')
    if groups is None:
        logger.error('Getting groups failed')
        return False

    # Check for the required group.
    for group in groups:
        if group_name('uploaders') == group['name']:
            return True

    # Group was not found, create it.
    data = {
        'name': settings.FILESERVICE_GROUP,
        'users': [{'email': settings.FILESERVICE_SERVICE_ACCOUNT}],
    }

    # Make the request.
    response = post(request, 'groups', data)
    if response is None:
        logger.error('Failed to create groups: {}'.format(response))
        return False

    # Get the upload group ID.
    upload_group_id = [group['id'] for group in response if group['name'] == group_name('UPLOADERS')][0]

    # Create the request to add the bucket to the upload group.
    bucket_data = {
        'buckets': [
            {'name': settings.FILESERVICE_AWS_BUCKET}
        ]
    }

    # Make the request.
    response = put(request, '/groups/{}/'.format(upload_group_id), bucket_data)

    return response


def create_file(request, filename, metadata, tags=[]):

    # Ensure groups exist.
    if not check_groups(request):
        logger.error('Groups do not exist or failed to create')
        return None

    # Build the request.
    data = {
        'permissions': [
            settings.FILESERVICE_GROUP
        ],
        'metadata': metadata,
        'filename': filename,
        'tags': tags,
    }

    # Make the request.
    file = post(request, '/api/file/', data)

    # Get the UUID.
    uuid = file['uuid']

    # Form the request for the file link
    params = {
        'cloud': 'aws',
        'bucket': settings.FILESERVICE_AWS_BUCKET,
    }

    # Make the request for an s3 presigned post.
    response = get(request, '/api/file/{}/post/'.format(uuid), params)

    return uuid, response


def uploaded_file(request, uuid, location_id):

    # Build the request.
    params = {
        'location': location_id
    }

    # Make the request.
    response = get(request, '/api/file/{}/uploadcomplete/'.format(uuid))

    return response is not None


def download_file(request, uuid):

    # Make the request.
    response = get(request, '/api/file/{}/download/'.format(uuid))

    return response['url']


def group_name(permission):
    return '{}__{}'.format(settings.FILESERVICE_GROUP, permission.upper())


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

