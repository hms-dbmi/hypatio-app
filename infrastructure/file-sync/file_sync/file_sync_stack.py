import re

from aws_cdk import (
    Duration,
    Stack,
    SecretValue,
    aws_iam,
    aws_kms,
    aws_secretsmanager,
    aws_ec2,
    aws_s3,
    aws_lambda,
    aws_lambda_python_alpha,
    aws_s3_notifications,
)
from constructs import Construct


class FileSyncStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        key = aws_kms.Key(
            self,
            "Key",
            alias=f"{construct_id}-key",
        )

        secret = aws_secretsmanager.Secret(
            self,
            "Secret",
            encryption_key=key,
            secret_name="/hms/dbmi/dbmisvc/portal/file-sync/notification-function",
            secret_object_value={
                "url": SecretValue.unsafe_plain_text(""),
                "token": SecretValue.unsafe_plain_text(""),
            },
        )

        function_role = aws_iam.Role(
            self,
            id="FunctionRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role used by notification function.",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
            ]
        )

        function_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                ],
                resources=[
                    key.key_arn,
                ]
            )
        )

        function_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecret*",
                    "secretsmanager:DescribeSecret*",
                ],
                resources=[
                    secret.secret_arn
                ]
            )
        )

        function = aws_lambda_python_alpha.PythonFunction(
            self,
            "Function",
            entry="notification-function",
            index="index.py",
            handler="lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            role=function_role,
            timeout=Duration.minutes(3),
            environment={
                "SECRET_ID": secret.secret_arn,
            },
        )

        # Iterate buckets and add permission
        for bucket_name in props["buckets"]:

            bucket = aws_s3.Bucket.from_bucket_name(
                self,
                "Bucket",
                bucket_name=bucket_name,
            )

            # Add it to the function
            function.add_permission(
                f"{''.join([t.title() for t in re.split('[^a-zA-Z0-9]', bucket_name)])}Permission",
                principal=aws_iam.ServicePrincipal('s3.amazonaws.com'),
                action="lambda:InvokeFunction",
                source_arn=bucket.bucket_arn,
                source_account=self.account,
            )

            # Add notification
            notification = aws_s3_notifications.LambdaDestination(function)

            # Add events notifications to bucket
            bucket.add_object_created_notification(notification)
            bucket.add_object_removed_notification(notification)
