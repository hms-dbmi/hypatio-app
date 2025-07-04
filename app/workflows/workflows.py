import json
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
from workflows.models import StepStateInitialization, WorkflowState
from workflows.models import StepState
from workflows.forms import RexplainVideoUploadForm
from workflows.forms import StepReviewForm

import logging
logger = logging.getLogger(__name__)


class WorkflowController(object):
    """
    Controller for managing a workflow.
    """
    template = "workflows/workflow.html"
    admin_template = "workflows/admin/workflow.html"

    def __init__(self, workflow_state, admin=False):
        self.workflow_state = workflow_state
        self.admin = admin

    def set_response_headers(self, response):
        """
        Sets any needed headers in the response for UI updates, etc.
        """
        pass

    def return_template_response(self, request, template = None, context = None) -> HttpResponse:
        """
        Builds and returns the response given the template and context.
        """
        if not template:
            template = self.template if not self.admin else self.admin_template

        if not context:
            context = {}

        # Add admin flag if set
        if self.admin:
            context["admin"] = self.admin

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
        logger.debug(f"[{self.__class__.__name__}][get]")

        # Retrieve step states
        step_states = self.workflow_state.get_ordered_step_states()

        # Build the context.
        context = {
            "workflow": self.workflow_state,
            "steps": step_states,
        }

        return self.return_template_response(request, self.template, context)

    def admin_get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step in admin mode.
        """
        logger.debug(f"[{self.__class__.__name__}][admin_get]")

        # Retrieve step states
        step_states = self.workflow_state.get_ordered_step_states()

        # Build context
        context = {
            "workflow": self.workflow_state,
            "steps": step_states,
        }

        return self.return_template_response(request, self.admin_template, context)

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

        # Change template for admin
        template = self.template if not self.admin else self.admin_template

        return self.return_template_response(request, template, context)


class StepController(object):
    """
    Controller for managing a step in a workflow.
    """
    template = "workflows/step.html"
    admin_template = "workflows/admin/step.html"

    def __init__(self, step_state, admin=False):
        self.step_state = step_state
        self.admin = admin
        self.step_state_changed = False

    def request_data_fields(self) -> list[str]:
        """
        Returns a list of key names for data fields to remove from data objects
        before saving them.
        """
        return [
            "ic-id", "_method", "ic-request", "ic-target-id", "ic-element-name",
            "ic-element-id", "ic-current-url", "ic-trigger-id", "ic-trigger-name",
            "csrfmiddlewaretoken"
        ]

    def get_dependent_urls(self, request) -> list[str]:
        """
        Returns the list of URLs for the StepState objects that depend on the
        current one. This is used to trigger refreshes of those StepState
        objects in the interface whenever a change is performed.
        """
        return [
            reverse(f"workflows:{request.resolver_match.url_name}", kwargs={"step_state_id": s.id})
            for s in self.step_state.get_dependents()
        ]

    def persist_data(self, data: dict[str, Any]):
        """
        Accepts the data from the step and persists it accordingly.
        """
        # Remove request fields
        cleaned_data = {k:v for k, v in data.items() if k not in self.request_data_fields()}
        self.step_state.data = cleaned_data
        self.step_state.save()

        # Mark the StepState as changed
        self.step_state_changed = True

    def set_response_headers(self, request, response):
        """
        Sets any needed headers in the response for UI updates, etc.
        """
        # Check for changed content
        if self.step_state_changed:

            # Add dependent URLs to the response headers to trigger refreshes
            refresh_urls = [reverse("workflows:step-state", kwargs={"step_state_id": self.step_state.id})]
            refresh_urls.extend(self.get_dependent_urls(request))

            # Add them as well as the current one
            #response["X-IC-Refresh"] = ",".join(refresh_urls)

    def return_response(self, request, response) -> HttpResponse:
        """
        Accepts an HttpResponse object and returns it, making any
        necessary updates to headers, etc. in the process.
        """
        # Set headers
        self.set_response_headers(request, response)

        return response

    def return_template_response(self, request, template = None, context = None) -> HttpResponse:
        """
        Builds and returns the response given the template and context.
        """
        if not template:
            template = self.template if not self.admin else self.admin_template

        if not context:
            context = {}

        # Add admin flag if set
        if self.admin:
            context["admin"] = self.admin

        # Add some constants to the context
        if not context.get("WorkflowStateStatus"):
            context["WorkflowStateStatus"] = WorkflowState.Status.__members__
        if not context.get("StepStateStatus"):
            context["StepStateStatus"] = StepState.Status.__members__

        # Make the response
        response = render(request, template, context)

        return self.return_response(request, response)

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug("[StepController][get]")
        context = {
            "step": self.step_state,
        }

        return self.return_template_response(request, self.template, context)

    def admin_get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step in admin mode.
        """
        logger.debug("[StepController][admin_get]")
        context = {
            "step": self.step_state,
        }

        return self.return_template_response(request, self.admin_template, context)

    def post(self, request, *args, **kwargs):
        """
        Handle input from the step.
        """
        logger.debug("[StepController][post]")

        # Save the data
        self.persist_data(request.POST)

        # Set the next status for the StepState
        #self.step_state.set_status()

        # Set new context
        context = {
            "step": self.step_state,
        }

        # Change template for admin
        template = self.template if not self.admin else self.admin_template

        return self.return_template_response(request, template, context)

    def admin_post(self, request, *args, **kwargs):
        """
        Handle input from the admin view of the step.
        """
        logger.debug("[StepController][admin_post]")

        # Set new context
        context = {
            "step": self.step_state,
        }

        return self.return_template_response(request, self.admin_template, context)

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
    admin_template = "workflows/admin/steps/form.html"

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

        return self.return_template_response(request, self.template, context)

    def admin_get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step with a form for admins.
        """
        logger.debug(f"[{self.__class__.__name__}][admin_get]")

        # Build the form
        form = self.step_state.step.form(initial=self.step_state.data)

        # Render it
        context = {
            "step": self.step_state,
            "form": form,
        }

        return self.return_template_response(request, self.admin_template, context)

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

        # Set the next status for the StepState
        #self.step_state.set_status()

        # Set new context
        context = {
            "step": self.step_state,
        }

        # Change template for admin
        template = self.template if not self.admin else self.admin_template

        return self.return_template_response(request, template, context)


class FileUploadStepController(StepController):
    """ Controller for managing a step that includes a form for uploading files."""
    template = "workflows/steps/upload-file.html"
    admin_template = "workflows/admin/steps/upload-file.html"

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

        # Change template for admin
        template = self.template if not self.admin else self.admin_template

        return self.return_template_response(request, template, context)

    def admin_get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step with a form for admins.
        """
        logger.debug(f"[{self.__class__.__name__}][admin_get]")

        # Include the DataProject
        data_project = self.step_state.step.workflow.get_data_project()

        # Render it
        context = {
            "step": self.step_state,
            "data_project": data_project,
        }

        # Check if a review is needed
        if self.step_state.step.review_required:

            # Add the form
            review_form = StepReviewForm(initial={
                "decided_by": request.user.id,
                "step_state": self.step_state.id,
            })

            context["review_form"] = review_form

        return self.return_template_response(request, self.admin_template, context)

    def post(self, request, *args, **kwargs):
        logger.debug("[FileUploadStepController][post]")

        # Check if a refresh
        if request.POST.get('refresh'):
            logger.debug("[FileUploadStepController][post] - Refresh requested")

            # Make context
            context = {
                "step": self.step_state,
            }

            return self.return_template_response(request, self.template, context)

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

        return self.return_response(request, JsonResponse(data=response))

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
            upload_data.pop("csrfmiddlewaretoken", None)
            upload_data.pop("location", None)

            # Add some more fields
            upload_data['submitted_by'] = request.user.email

            # Make the request to FileService.
            if not fileservice.uploaded_file(request, data['uuid'], data['location']):
                logger.error('[FileUploadStepController][patch] Fileservice uploadCompleted failed')
            else:
                logger.debug('[FileUploadStepController][patch] Fileservice uploadCompleted succeeded')

                # Save the data
                self.persist_data(data)

                # Set the next status for the StepState
                #self.step_state.set_status()

            return self.return_response(request, HttpResponse(status=200))

        except Exception as e:
            logger.exception(e)
            return HttpResponse(status=500)


class VideoStepController(StepController):
    """
    Controller for managing a step in a workflow.
    """
    template = "workflows/steps/video.html"
    admin_template = "workflows/admin/steps/video.html"

    def get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step.
        """
        logger.debug(f"[{self.__class__.__name__}][get]")

        context = {
            "step": self.step_state,
        }

        # Check if the step has been initialized
        if self.step_state.is_initialized:
            logger.debug(f"[{self.__class__.__name__}][get] Step is initialized.")

            # Get the Fileservice UUID from the initialization
            fileservice_uuid = self.step_state.initialization.data.get("uuid")

            # Get a pre-signed URL from Fileservice
            video_url = dbmi_fileservice.get_archivefile_download_url(uuid=fileservice_uuid)

            # Set it in context
            context["video_url"] = video_url

        return self.return_template_response(request, self.template, context)

    def admin_get(self, request, *args, **kwargs):
        """
        Build the context for rendering the step with a form for admins.
        """
        logger.debug(f"[{self.__class__.__name__}][admin_get]")

        # Render it
        context = {
            "step": self.step_state,
        }

        # If admin and not initialized, add the form.
        if not self.step_state.is_initialized:

            # Initialize the form class
            form = RexplainVideoUploadForm()

            # Render it
            context["form"] = form

            # Set allowed media types
            context["allowed_media_types"] = [
                "video/mp4",
                "video/webm",
                "video/ogg",
                "video/x-matroska",
                "video/quicktime",
                "video/x-msvideo",
                "video/x-flv",
            ]

        return self.return_template_response(request, self.admin_template, context)

    def post(self, request, *args, **kwargs):
        logger.debug(f"[{self.__class__.__name__}][post]")

        # Parse the data
        if request.POST.get("video-tracking"):
            data = json.loads(request.POST.get("video-tracking"))
        else:
            data = []

        # Save the data
        self.persist_data({"video-tracking": data})

        # Set the next status for the StepState
        #self.step_state.set_status()

        # Set new context
        context = {
            "step": self.step_state,
        }

        return self.return_template_response(request, self.template, context)

    def admin_post(self, request, *args, **kwargs):
        logger.debug(f"[{self.__class__.__name__}][admin_post]")

        # Check if a refresh
        if request.POST.get('refresh'):
            logger.debug(f"[{self.__class__.__name__}][admin_post] - Refresh requested")

            # Make context
            context = {
                "step": self.step_state,
            }

            return self.return_template_response(request, self.admin_template, context)

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

        return self.return_response(request, JsonResponse(data=response))

    def admin_patch(self, request, *args, **kwargs):
        logger.debug(f"[{self.__class__.__name__}][admin_patch]")

        # Get the data.
        data = QueryDict(request.body)
        logger.debug(f"[{self.__class__.__name__}][admin_patch] Data: {data}")

        try:
            # Prepare a json that holds information about the file and the original submission form.
            # This is used later as included metadata when downloading the participant's submission.
            upload_data = copy(data)

            # Remove a few unnecessary fields.
            upload_data.pop("csrfmiddlewaretoken", None)
            upload_data.pop("location", None)

            # Add some more fields
            upload_data['submitted_by'] = request.user.email

            # Make the request to FileService.
            if not fileservice.uploaded_file(request, data['uuid'], data['location']):
                logger.error(f"[{self.__class__.__name__}][admin_patch] Fileservice uploadCompleted failed")
            else:
                logger.debug(f"[{self.__class__.__name__}][admin_patch] Fileservice uploadCompleted succeeded")

                # Create an initialization object
                StepStateInitialization.objects.create(
                    step_state=self.step_state,
                    data={
                        "uuid": data.get("uuid"),
                        "location": data.get("location"),
                        "filename": data.get("filename"),
                    },
                    initialized_by=request.user,
                )

                # Mark the StepState as changed
                self.step_state_changed = True

            return self.return_response(request, HttpResponse(status=200))

        except Exception as e:
            logger.exception(e)
            return HttpResponse(status=500)
