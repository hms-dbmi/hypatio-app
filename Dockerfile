FROM python:3.6-alpine3.11 AS builder

# Install dependencies
RUN apk add --update \
    build-base \
    g++ \
    libffi-dev \
    mariadb-dev

# Add requirements
ADD requirements /requirements

# Install Python packages
RUN pip install -r /requirements/requirements.txt

FROM hmsdbmitc/dbmisvc:alpine-python3.6-0.1.0

RUN apk add --no-cache --update \
    bash \
    nginx \
    curl \
    openssl \
    jq \
    mariadb-connector-c \
  && rm -rf /var/cache/apk/*

# Copy pip packages from builder
COPY --from=builder /root/.cache /root/.cache

# Add requirements
ADD requirements /requirements

# Install Python packages
RUN pip install -r /requirements/requirements.txt

# Copy app source
COPY /app /app

# Set the build env
ENV DBMI_ENV=prod

# Set app parameters
ENV DBMI_PARAMETER_STORE_PREFIX=dbmi.hypatio.${DBMI_ENV}
ENV DBMI_PARAMETER_STORE_PRIORITY=true
ENV DBMI_AWS_REGION=us-east-1

# App config
ENV DBMI_APP_WSGI=hypatio
ENV DBMI_APP_ROOT=/app
ENV DBMI_APP_DB=true
ENV DBMI_APP_DOMAIN=portal.dbmi.hms.harvard.edu

# Load balancing
ENV DBMI_LB=true

# SSL and load balancing
ENV DBMI_SSL=true
ENV DBMI_CREATE_SSL=true
ENV DBMI_SSL_PATH=/etc/nginx/ssl

# Static files
ENV DBMI_STATIC_FILES=true
ENV DBMI_APP_STATIC_URL_PATH=/static
ENV DBMI_APP_STATIC_ROOT=/app/assets

# Healthchecks
ENV DBMI_HEALTHCHECK=true
ENV DBMI_HEALTHCHECK_PATH=/healthcheck
ENV DBMI_APP_HEALTHCHECK_PATH=/healthcheck