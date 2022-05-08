FROM hmsdbmitc/dbmisvc:debian11-slim-python3.10-0.3.3 AS builder

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bzip2 \
        gcc \
        default-libmysqlclient-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Add requirements
ADD requirements.* /

# Build Python wheels with hash checking
RUN pip install -U wheel \
    && pip wheel -r /requirements.txt \
        --wheel-dir=/root/wheels

FROM hmsdbmitc/dbmisvc:debian11-slim-python3.10-0.3.3

# Copy Python wheels from builder
COPY --from=builder /root/wheels /root/wheels

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
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
