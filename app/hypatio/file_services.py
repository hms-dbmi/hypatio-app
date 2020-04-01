import os
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

    return {
        'Authorization': '{} {}'.format(settings.FILESERVICE_AUTH_HEADER_PREFIX, settings.FILESERVICE_SERVICE_TOKEN),
        'Content-Type': 'application/json'
    }


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

    # Group was not found, create it, specifying passed admins
    data = {
        'name': settings.FILESERVICE_GROUP.upper(),
        'users': [{'email': settings.FILESERVICE_SERVICE_ACCOUNT}],
        'buckets': [{'name': settings.FILESERVICE_AWS_BUCKET}],
    }

    # Make the request
    groups = post(request, 'groups', data)
    if not groups:
        logger.info('Failed to create groups')
        return False

    # Make the request.
    data = {'buckets': [{'name': settings.FILESERVICE_AWS_BUCKET}]}
    for group in groups:

        # Make the request
        response = put(request, '/groups/{}/'.format(group['id']), data)
        if response:
            logger.info('Added bucket "{}" to group "{}"'.format(
                settings.FILESERVICE_AWS_BUCKET, group['name']
            ))
        else:
            logger.info('Failed to add bucket "{}" to group "{}"'.format(
                settings.FILESERVICE_AWS_BUCKET, group['name']
            ))

    return True


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
        'expires': 100,
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
    response = get(request, '/api/file/{}/uploadcomplete/'.format(uuid), params)

    return response is not None


def get_fileservice_download_url(request, uuid):
    """
    Returns a download URL generated by FileService.
    """

    # Make the request.
    response = get(request, '/api/file/{}/download/'.format(uuid))

    return response['url']


def group_name(permission):
    return '{}__{}'.format(settings.FILESERVICE_GROUP, permission.upper())


def _s3_client():
    # Get the service client with sigv4 configured
    return boto3.client('s3', config=Config(signature_version='s3v4'))


def get_download_url(file_name, expires_in=3600):
    """
    Returns an S3 URL for project related files not tracked by fileservice.
    """

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
    """
    Enables uploading of files directly to the Hypatio S3 bucket without fileservice tracking.
    """

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


def host_file(request, file_uuid, file_location, file_name):
    """
    Copies a file from the Fileservice bucket to the Hypatio hosted files bucket
    """
    try:
        # Make the request.
        file = get(request, '/api/file/{}/'.format(file_uuid))
        logger.debug(file)

        # Perform the request to copy the file
        source = {'Bucket': settings.FILESERVICE_AWS_BUCKET, 'Key': file['locations'][0]['url'].split('/', 3)[3]}
        key = os.path.join(file_location, file_name)

        logger.debug(f'Fileservice: Copying {source["Bucket"]}/{source["Key"]}'
                     f' to {settings.S3_BUCKET}/{key}')

        # Generate the URL to get the file object
        _s3_client().copy_object(
            CopySource=source,
            Bucket=settings.S3_BUCKET,
            Key=key,
        )

        return True

    except Exception as e:
        logger.exception('[file_services][host_file] Error: {}'.format(e), exc_info=True, extra={
            'request': request, 'file_uuid': file_uuid, 'file_location': file_location, 'file_name': file_name
        })

    return False
