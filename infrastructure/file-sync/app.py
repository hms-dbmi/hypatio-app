#!/usr/bin/env python3
import os

import aws_cdk as cdk

from file_sync.file_sync_stack import FileSyncStack

# Commands
# Deploy: cdk deploy --all --profile hms-dbmi-lzprod-dbmisvc-dev -c env=dev

app = cdk.App()

environments = app.node.try_get_context("environments")
env = app.node.try_get_context("env")
props = environments[app.node.try_get_context("env")]

cdk.Tags.of(app).add("Why", "DBMISVC")
cdk.Tags.of(app).add("Code", "DBMISVC")
cdk.Tags.of(app).add("Project", "DBMISVC")
cdk.Tags.of(app).add("Product", "Data Portal")
cdk.Tags.of(app).add("Owner", "bryan_larson@hms.harvard.edu")
cdk.Tags.of(app).add("Contact", "bryan_larson@hms.harvard.edu")
cdk.Tags.of(app).add("Organization", "HMS")
cdk.Tags.of(app).add("Department", "DBMI")
cdk.Tags.of(app).add("Group", "Tech Dev Core")
cdk.Tags.of(app).add("NIH Funded", "no")
cdk.Tags.of(app).add("Environment", env)
cdk.Tags.of(app).add("HMS Data Security Level", props["hms-data-security-level"])

dev_stack = FileSyncStack(
    app,
    "dbmisvc-portal-file-sync",
    props=props,
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION'),
    ),
)

app.synth()
