#!/bin/bash

SITE_URL=$(aws ssm get-parameters --names $PS_PATH.site_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
ALLOWED_HOSTS=$(aws ssm get-parameters --names $PS_PATH.allowed_hosts --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
DJANGO_SECRET=$(aws ssm get-parameters --names $PS_PATH.django_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_DOMAIN_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_domain --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_CLIENT_ID_LIST=$(aws ssm get-parameters --names $PS_PATH.auth0_client_id_list --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_SECRET_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_SUCCESS_URL_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_success_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_LOGOUT_URL_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_logout_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
COOKIE_DOMAIN=$(aws ssm get-parameters --names $PS_PATH.cookie_domain --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

MYSQL_USERNAME_VAULT=$(aws ssm get-parameters --names $PS_PATH.mysql_username --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
MYSQL_PASSWORD_VAULT=$(aws ssm get-parameters --names $PS_PATH.mysql_pw --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
MYSQL_HOST_VAULT=$(aws ssm get-parameters --names $PS_PATH.mysql_host --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
MYSQL_PORT_VAULT=$(aws ssm get-parameters --names $PS_PATH.mysql_port --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

EMAIL_HOST=$(aws ssm get-parameters --names $PS_PATH.email_host --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
EMAIL_HOST_USER=$(aws ssm get-parameters --names $PS_PATH.email_host_user --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
EMAIL_HOST_PASSWORD=$(aws ssm get-parameters --names $PS_PATH.email_host_password --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
EMAIL_PORT=$(aws ssm get-parameters --names $PS_PATH.email_port --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

RAVEN_URL=$(aws ssm get-parameters --names $PS_PATH.raven_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export COOKIE_DOMAIN
export SITE_URL=$SITE_URL
export ALLOWED_HOSTS=$ALLOWED_HOSTS
export SECRET_KEY=$DJANGO_SECRET
export AUTH0_DOMAIN=$AUTH0_DOMAIN_VAULT
export AUTH0_CLIENT_ID_LIST=$AUTH0_CLIENT_ID_LIST
export AUTH0_SECRET=$AUTH0_SECRET_VAULT
export AUTH0_SUCCESS_URL=$AUTH0_SUCCESS_URL_VAULT
export AUTH0_LOGOUT_URL=$AUTH0_LOGOUT_URL_VAULT

export MYSQL_USERNAME=$MYSQL_USERNAME_VAULT
export MYSQL_PASSWORD=$MYSQL_PASSWORD_VAULT
export MYSQL_HOST=$MYSQL_HOST_VAULT
export MYSQL_PORT=$MYSQL_PORT_VAULT

export EMAIL_HOST
export EMAIL_HOST_USER
export EMAIL_HOST_PASSWORD
export EMAIL_PORT

export RAVEN_URL

ACCOUNT_SERVER_URL=$(aws ssm get-parameters --names $PS_PATH.authentication_login_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SCIREG_SERVER_URL=$(aws ssm get-parameters --names $PS_PATH.register_user_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTHZ_BASE=$(aws ssm get-parameters --names $PS_PATH.authorization_server_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export ACCOUNT_SERVER_URL
export SCIREG_SERVER_URL
export AUTHZ_BASE

export RECAPTCHA_KEY=$(aws ssm get-parameters --names $PS_PATH.recaptcha_key --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export RECAPTCHA_CLIENT_ID=$(aws ssm get-parameters --names $PS_PATH.recaptcha_client_id --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export EMAIL_CONFIRM_SUCCESS_URL=$(aws ssm get-parameters --names $PS_PATH.email_confirm_success_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export S3_AWS_ACCESS_KEY_ID=$(aws ssm get-parameters --names $PS_PATH.s3_aws_access_key_id --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export S3_AWS_SECRET_ACCESS_KEY=$(aws ssm get-parameters --names $PS_PATH.s3_aws_secret_access_key --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export S3_BUCKET=$(aws ssm get-parameters --names $PS_PATH.s3_bucket --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export FILESERVICE_API_URL=$(aws ssm get-parameters --names $PS_PATH.fileservice_api_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export FILESERVICE_GROUP=$(aws ssm get-parameters --names $PS_PATH.fileservice_group --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export FILESERVICE_SERVICE_ACCOUNT=$(aws ssm get-parameters --names $PS_PATH.fileservice_service_account --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export FILESERVICE_SERVICE_TOKEN=$(aws ssm get-parameters --names $PS_PATH.fileservice_service_token --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

SSL_KEY=$(aws ssm get-parameters --names $PS_PATH.ssl_key --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN1=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain1 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN2=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain2 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN3=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain3 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

SSL_CERT_CHAIN="$SSL_CERT_CHAIN1$SSL_CERT_CHAIN2$SSL_CERT_CHAIN3"

echo $SSL_KEY | base64 -d >> /etc/nginx/ssl/server.key
echo $SSL_CERT_CHAIN | base64 -d >> /etc/nginx/ssl/server.crt

cd /app/

python manage.py migrate
python manage.py loaddata hostedfileset
python manage.py loaddata hostedfile
if [ ! -d static ]; then
  mkdir static
fi
python manage.py collectstatic --no-input

/etc/init.d/nginx restart

chown -R www-data:www-data /app

gunicorn hypatio.wsgi:application -b 0.0.0.0:8000  --user=www-data --group=www-data