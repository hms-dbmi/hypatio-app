import json
import boto3
import os
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Event: {event}")

    # Get secrets from Secrets Manager
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(
        SecretId=os.environ["SECRET_ID"],
    )
    secrets = json.loads(response['SecretString'])

    # Get the portal token and URL
    url = secrets["url"]
    token = secrets["token"]

    # Set headers
    headers = {
        "Authorization": f"Token {token}",
    }

    # Forward it to the Data Portal
    logger.info(f"POSTing event(s) to '{url}'")
    response = requests.post(url, headers=headers, json=event["Records"])

    return response.json()
