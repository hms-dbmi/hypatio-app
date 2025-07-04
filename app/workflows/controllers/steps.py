from django.utils import timezone
import boto3
from botocore.exceptions import ClientError

from workflows.workflows import StepController
from workflows.models import Workflow
from workflows.models import WorkflowState
from workflows.models import StepState
from workflows.models import Step

import logging
logger = logging.getLogger(__name__)


class RexplainVideoStepController(StepController):
    """
    Controller for managing a step in a workflow.
    """
    template = "workflows/steps/rexplain-video.html"

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug(f"[{self.__class__.__name__}][get]")
        
        # Set initial context
        context = {
            "step": self.step_state,
        }
        
        # Check for initialization
        if self.step_state.is_initialized():
            logger.debug(f"[{self.__class__.__name__}][get] Step is initialized.")
            
            try:
                # Get S3 file details from the step state initialization
                bucket = self.step_state.initialization.data["bucket"]
                key = self.step_state.initialization.data["key"]
                
                # Set the expiration time for the presigned URL
                expiration = 7200
                
                # Generate a presigned URL for the S3 object
                s3_client = boto3.client("s3")
                context["video_url"] = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expiration,
                )

            except (Exception, ClientError) as e:
                logger.error(f"[{self.__class__.__name__}][get] Error retrieving video URL: {e}")

        return self.return_response(request, self.template, context)

    def post(self, request, *args, **kwargs):
        logger.debug(f"[{self.__class__.__name__}][post]")

        # Save the data
        self.persist_data(request.POST)

        # Update the state
        self.set_completed(completed_at=timezone.now())

        # Set new context
        context = {
            "step": self.step_state,
        }

        return self.return_response(request, self.template, context)
