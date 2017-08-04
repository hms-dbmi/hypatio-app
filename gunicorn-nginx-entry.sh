#!/bin/bash

DJANGO_SECRET=$(aws ssm get-parameters --names $PS_PATH.django_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_DOMAIN_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_domain --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_CLIENT_ID_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_client_id --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_SECRET_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_SUCCESS_URL_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_success_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTH0_LOGOUT_URL_VAULT=$(aws ssm get-parameters --names $PS_PATH.auth0_logout_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
COOKIE_DOMAIN=$(aws ssm get-parameters --names $PS_PATH.cookie_domain --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

EMAIL_HOST=$(aws ssm get-parameters --names $PS_PATH.email_host --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
EMAIL_HOST_USER=$(aws ssm get-parameters --names $PS_PATH.email_host_user --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
EMAIL_HOST_PASSWORD=$(aws ssm get-parameters --names $PS_PATH.email_host_password --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
EMAIL_PORT=$(aws ssm get-parameters --names $PS_PATH.email_port --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export COOKIE_DOMAIN
export SECRET_KEY=$DJANGO_SECRET
export AUTH0_DOMAIN=$AUTH0_DOMAIN_VAULT
export AUTH0_CLIENT_ID=$AUTH0_CLIENT_ID_VAULT
export AUTH0_SECRET=$AUTH0_SECRET_VAULT
export AUTH0_SUCCESS_URL=$AUTH0_SUCCESS_URL_VAULT
export AUTH0_LOGOUT_URL=$AUTH0_LOGOUT_URL_VAULT

export EMAIL_HOST
export EMAIL_HOST_USER
export EMAIL_HOST_PASSWORD
export EMAIL_PORT

ACCOUNT_SERVER_URL=$(aws ssm get-parameters --names $PS_PATH.authentication_login_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SCIREG_SERVER_URL=$(aws ssm get-parameters --names $PS_PATH.register_user_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
AUTHZ_BASE=$(aws ssm get-parameters --names $PS_PATH.authorization_server_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export ACCOUNT_SERVER_URL
export SCIREG_SERVER_URL
export AUTHZ_BASE

SSL_KEY=$(aws ssm get-parameters --names $PS_PATH.ssl_key --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN1=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain1 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN2=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain2 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN3=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain3 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

SSL_CERT_CHAIN="$SSL_CERT_CHAIN1$SSL_CERT_CHAIN2$SSL_CERT_CHAIN3"

echo $SSL_KEY | base64 -d >> /etc/nginx/ssl/server.key
echo $SSL_CERT_CHAIN | base64 -d >> /etc/nginx/ssl/server.crt

cd /app/

python manage.py migrate
python manage.py loaddata dataprojects
if [ ! -d static ]; then
  mkdir static
fi
python manage.py collectstatic --no-input

/etc/init.d/nginx restart

chown -R www-data:www-data /app

gunicorn hypatio.wsgi:application  --user=www-data --group=www-data