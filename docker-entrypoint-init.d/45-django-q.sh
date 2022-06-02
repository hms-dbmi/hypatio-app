#!/bin/bash -e

# Create the Django cache table as needed by Q
python ${DBMI_APP_ROOT}/manage.py createcachetable

# Start the Q cluster
python ${DBMI_APP_ROOT}/manage.py qcluster &
