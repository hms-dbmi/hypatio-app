#!/bin/bash

# Ensure scratch space for the PDF generator exists and is writable
mkdir -p $DBMI_APP_ROOT/pdf/temp
chown -R $DBMI_NGINX_USER:$DBMI_NGINX_USER $DBMI_APP_ROOT/pdf/temp
chmod -R 775 $DBMI_APP_ROOT/pdf/temp

echo "$DBMI_APP_ROOT/pdf/temp is ready!"
