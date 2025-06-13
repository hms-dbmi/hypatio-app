from copy import copy
from typing import Any
from datetime import datetime

from django.views import View
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.http import QueryDict
from django.core import exceptions
from django.urls import reverse
from dbmi_client import fileservice as dbmi_fileservice

from hypatio import file_services as fileservice
from workflows.models import WorkflowState
from workflows.models import StepState

import logging
logger = logging.getLogger(__name__)


class WorkflowController:
    """
    Controller for managing a workflow.
    """
    template = "workflows/workflow.html"

    def __init__(self, workflow_state):
        self.workflow_state = workflow_state

    def set_response_headers(self, response):
        """
        Sets any needed headers in the response for UI updates, etc.
        """
        pass

    def return_response(self, request, template = None, context = None) -> HttpResponse:
        """
        Builds and returns the response given the template and context.
        """
        if not template:
            template = self.template

        if not context:
            context = {}

        # Add some constants to the context
        if not context.get("WorkflowStateStatus"):
            context["WorkflowStateStatus"] = WorkflowState.Status.__members__
        if not context.get("StepStateStatus"):
            context["StepStateStatus"] = StepState.Status.__members__

        # Make the response
        response = render(request, template, context)

        # Set any headers needed
        self.set_response_headers(response)

        return response

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the workflow.
        """
        # Retrieve step states
        step_states = self.workflow_state.get_ordered_step_states()

        # Build the context.
        context = {
            "workflow": self.workflow_state,
            "steps": step_states,
        }

        # Render it.
        return self.return_response(request, self.template, context)

    def post(self, request, *args, **kwargs):
        """
        Build the context for rendering the workflow.
        """
        logger.debug(f"[StepController][post] {request.POST}")

        # Check data for status
        status = request.POST.get("workflow-state-status")
        try:
            WorkflowState.Status(status)

            # Set it and save it
            self.workflow_state.status = status
            self.workflow_state.save()

        except Exception:
            logger.error(f"[WorkflowController][post] Invalid status: {status}")
            return HttpResponse(status=400)

        # Retrieve step states
        step_states = self.workflow_state.get_ordered_step_states()

        # Build the context.
        context = {
            "workflow": self.workflow_state,
            "steps": step_states,
        }

        # Render it.
        return self.return_response(request, self.template, context)


class StepController:
    """
    Controller for managing a step in a workflow.
    """
    template = "workflows/step.html"

    def __init__(self, step_state):
        self.step_state = step_state

    def request_data_fields(self) -> list[str]:
        """
        Returns a list of key names for data fields to remove from data objects
        before saving them.
        """
        return [
            "ic-id", "_method", "ic-request", "ic-target-id",
            "ic-element-id", "ic-current-url", "ic-trigger-id", "ic-trigger-name",
            "csrfmiddlewaretoken"
        ]

    def persist_data(self, data: dict[str, Any]):
        """
        Accepts the data from the step and persists it accordingly.
        """
        # Remove request fields
        cleaned_data = {k:v for k, v in data.items() if k not in self.request_data_fields()}
        self.step_state.data = cleaned_data
        self.step_state.save()

    def set_completed(self, completed_at: datetime = timezone.now()):
        """
        Sets the StepState as completed and saves the data.
        """
        # Set is as completed, if not indefinite
        if not self.step_state.step.indefinite:
            self.step_state.status = StepState.Status.Completed.value
            self.step_state.completed_at = completed_at
            self.step_state.save()

    def set_response_headers(self, response):
        """
        Sets any needed headers in the response for UI updates, etc.
        """
        pass

    def return_response(self, request, template = None, context = None) -> HttpResponse:
        """
        Builds and returns the response given the template and context.
        """
        if not template:
            template = self.template

        if not context:
            context = {}

        # Add some constants to the context
        if not context.get("WorkflowStateStatus"):
            context["WorkflowStateStatus"] = WorkflowState.Status.__members__
        if not context.get("StepStateStatus"):
            context["StepStateStatus"] = StepState.Status.__members__

        # Make the response
        response = render(request, template, context)

        # Set any headers needed
        self.set_response_headers(response)

        return response

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug("[StepController][get]")
        context = {
            "step": self.step_state,
        }

        return self.return_response(request, self.template, context)

    def post(self, request, *args, **kwargs):
        """
        Handle input from the step.
        """
        logger.debug("[StepController][post]")

        # Save the data
        self.persist_data(request.POST)

        # Update the state
        self.set_completed(completed_at=timezone.now())

        # Set new context
        context = {
            "step": self.step_state,
        }

        return self.return_response(request, self.template, context)

    @classmethod
    def controller_classes(cls) -> list[(str, str)]:
        """
        Returns a list of tuples containing a classes fully-qualified name and its short name.
        """
        # Get all subclasses of StepController
        subclasses = set(StepController.__subclasses__()).union([s for c in cls.__subclasses__() for s in c.controller_classes()])
        return [(f"{subclass.__module__}.{subclass.__name__}", subclass.__name__) for subclass in subclasses if subclass != StepController]


class FormStepController(StepController):
    """ Controller for managing a step that includes a form."""
    template = "workflows/steps/form.html"

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step with a form.
        """
        logger.debug("[FormStepController][get]")

        # Initialize the form class
        form = self.step_state.step.form()

        # Render it
        context = {
            "step": self.step_state,
            "form": form,
        }

        return self.return_response(request, self.template, context)

    def post(self, request, *args, **kwargs):
        """
        Handle input from the form on the step.
        """
        logger.debug("[FormStepController][post]")

        # Initialize the form class
        form = self.step_state.step.form(request.POST)
        if not form.is_valid():
            logger.debug(f"[FormStepController][post] - Form is not valid: {form.errors.as_json()}")
            return HttpResponse(form.errors.as_json(), status=400)

        # Save the data
        self.persist_data(request.POST)

        # Update the state
        self.set_completed(completed_at=timezone.now())

        # Set new context
        context = {
            "step": self.step_state,
        }

        return self.return_response(request, self.template, context)


class FileUploadStepController(StepController):
    """ Controller for managing a step that includes a form for uploading files."""
    template = "workflows/steps/upload-file.html"

    def get(self, request, *args, **kwargs):
        """
        Handle input from the form on the step.
        """
        logger.debug("[FileUploadStepController][get]")

        # Initialize the form class
        form = self.step_state.step.form()

        # Render it
        context = {
            "step": self.step_state,
            "form": form,
            "file_type": "zip",
            "file_content_types": [m.value for m in self.step_state.step.allowed_media_types.all()],
        }

        return self.return_response(request, self.template, context)

    def post(self, request, *args, **kwargs):
        logger.debug("[FileUploadStepController][post]")

        # Check if a refresh
        if request.POST.get('refresh'):
            logger.debug("[FileUploadStepController][post] - Refresh requested")

            # Make context
            context = {
                "step": self.step_state,
            }

            return self.return_response(request, self.template, context)

        # Assembles the form and runs validation.
        filename = request.POST.get('filename')

        if not filename:
            return HttpResponse('Filename are required', status=400)

        # Prepare the metadata.
        metadata = {
            'uploader': request.user.email,
            'type': 'file-upload',
            'app': 'hypatio',
        }

        # Create a new record in fileservice for this file and get back information on where it should live in S3.
        uuid, response = fileservice.create_file(request, filename, metadata)
        post = response['post']
        location = response['locationid']

        # Form the data for the File object.
        file = {'uuid': uuid, 'location': location, 'filename': filename}
        logger.debug('File: {}'.format(file))

        response = {
            'post': post,
            'file': file,
        }
        logger.debug('Response: {}'.format(post))

        return JsonResponse(data=response)

    def patch(self, request, *args, **kwargs):
        logger.debug("[FileUploadStepController][patch]")

        # Get the data.
        data = QueryDict(request.body)
        logger.debug(f'[FileUploadStepController][patch] Data: {data}')

        try:
            # Prepare a json that holds information about the file and the original submission form.
            # This is used later as included metadata when downloading the participant's submission.
            upload_data = copy(data)

            # Remove a few unnecessary fields.
            del upload_data['csrfmiddlewaretoken']
            del upload_data['location']

            # Add some more fields
            upload_data['submitted_by'] = request.user.email

            # Make the request to FileService.
            if not fileservice.uploaded_file(request, data['uuid'], data['location']):
                logger.error('[FileUploadStepController][patch] Fileservice uploadCompleted failed')
            else:
                logger.debug('[FileUploadStepController][patch] Fileservice uploadCompleted succeeded')

                # Save the data
                self.persist_data(request.POST)

                # Update the state
                self.set_completed(completed_at=timezone.now())

            return HttpResponse(status=200)

        except Exception as e:
            logger.exception(e)
            return HttpResponse(status=500)


class VideoStepController(StepController):
    """
    Controller for managing a step in a workflow.
    """
    template = "workflows/steps/video.html"

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug("[VideoStepController][get]")

        context = {
            "step": self.step_state,
            "thumbnail": self.step_state.step.thumbnail_url,
            "video": self.step_state.step.video_url,
        }

        return self.return_response(request, self.template, context)

    def post(self, request, *args, **kwargs):
        logger.debug("[VideoStepController][post]")

        # Save the data
        self.persist_data(request.POST)

        # Update the state
        self.set_completed(completed_at=timezone.now())

        # Set new context
        context = {
            "step": self.step_state,
        }

        return self.return_response(request, self.template, context)
