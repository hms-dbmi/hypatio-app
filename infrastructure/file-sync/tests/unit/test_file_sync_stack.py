import aws_cdk as core
import aws_cdk.assertions as assertions

from file_sync.file_sync_stack import FileSyncStack

# example tests. To run these tests, uncomment this file along with the example
# resource in file_sync/file_sync_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = FileSyncStack(app, "file-sync")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
