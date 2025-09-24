# Set arch
ARG BUILD_ARCH=amd64
ARG DBMISVC_IMAGE=hmsdbmitc/dbmisvc:debian12-slim-python3.11-0.7.2

FROM ${DBMISVC_IMAGE} AS builder

ARG BUILD_ARCH

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bzip2 \
        gcc \
        default-libmysqlclient-dev \
        libssl-dev \
        pkg-config \
        libfontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install requirements for PDF generation
ADD phantomjs-2.1.1-${BUILD_ARCH}.tar.gz /tmp/

# Add requirements
ADD requirements.* /

# Build Python wheels with hash checking
RUN pip install -U wheel \
    && pip wheel -r /requirements.txt \
        --wheel-dir=/root/wheels

FROM ${DBMISVC_IMAGE}

ARG APP_NAME="dbmi-data-portal"
ARG APP_CODENAME="hypatio"
ARG VERSION
ARG COMMIT
ARG DATE
ARG BUILD_ARCH

LABEL org.label-schema.schema-version=1.0 \
    org.label-schema.vendor="HMS-DBMI" \
    org.label-schema.version=${VERSION} \
    org.label-schema.name=${APP_NAME} \
    org.label-schema.build-date=${DATE} \
    org.label-schema.description="DBMI Data Portal" \
    org.label-schema.url="https://github.com/hms-dbmi/hypatio-app" \
    org.label-schema.vcs-url="https://github.com/hms-dbmi/hypatio-app" \
    org.label-schema.vcf-ref=${COMMIT}

# Copy PhantomJS binary
COPY --from=builder /tmp/phantomjs /usr/local/bin/phantomjs

# Copy Python wheels from builder
COPY --from=builder /root/wheels /root/wheels

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libfontconfig \
        default-libmysqlclient-dev \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Add requirements files
ADD requirements.* /

# Install Python packages from wheels
RUN pip install --no-index \
        --find-links=/root/wheels \
        --force-reinstall \
        # Use requirements without hashes to allow using wheels.
        # For some reason the hashes of the wheels change between stages
        # and Pip errors out on the mismatches.
        -r /requirements.in

# Setup entry scripts
ADD docker-entrypoint-init.d/* /docker-entrypoint-init.d/

# Copy app source
COPY /app /app

# Set the build env
ENV DBMI_ENV=prod

# Set app parameters
ENV DBMI_PARAMETER_STORE_PREFIX=dbmi.hypatio.${DBMI_ENV}
ENV DBMI_PARAMETER_STORE_PRIORITY=true
ENV DBMI_AWS_REGION=us-east-1

# App config
ENV DBMI_APP_NAME=${APP_NAME}
ENV DBMI_APP_CODENAME=${APP_CODENAME}
ENV DBMI_APP_VERSION=${VERSION}
ENV DBMI_APP_COMMIT=${COMMIT}
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

# File proxy
ENV DBMI_FILE_PROXY=true
ENV DBMI_FILE_PROXY_PATH=/proxy
