from typing import Optional
import json
from http import HTTPStatus

from django.http import HttpRequest
from django.conf import settings
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from furl import furl
import nh3

from projects.models import DataProjectWorkflow

from workflows.controllers import BaseController
from workflows.controllers import get_controller_choices
from workflows.forms import StepReviewForm
from workflows.models import StepState
from workflows.forms import StepStateFileForm
from workflows.models import StepStateInitialization
from workflows.models import StepStateReview
from workflows.models import StepStateVersion

import logging
logger = logging.getLogger(__name__)


def get_step_controller_choices() -> list[(str, str)]:
    """
    Returns a list of tuples containing a class's fully-qualified name and its short name for step controllers.
    """
    return get_controller_choices(BaseStepController)


class BaseStepController(BaseController):
    """
    Controller for a step.
    """
    def __init__(self, step_state, is_administration=False):
        self.step_state = step_state
        self.is_administration = is_administration

    @classmethod
    def request_meta_fields(cls) -> list[str]:
        """
        Returns a list of key names for data fields to remove from data objects
        before saving them.
        """
        return [
            "ic-id", "_method", "ic-request", "ic-target-id", "ic-element-name",
            "ic-element-id", "ic-current-url", "ic-trigger-id", "ic-trigger-name",
            "csrfmiddlewaretoken"
        ]

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "Base Step Controller"

    def template(self, request) -> str:
        """
        Returns the name of the template to be used for rendering the StepState object.
        """
        return "workflows/step.html" if not self.is_administration else "workflows/admin/step.html"

    def render_context(self, request) -> dict:
        """
        Returns the context to be used for rendering the StepState object.
        """
        context = {
            "StepStateStatus": StepState.Status.__members__,
            "step": self.step_state,
        }

        # Check if admin
        if self.is_administration:

            # Add it to context
            context["is_administration"] = True

            # Check if a review is needed
            if self.step_state.step.review_required:

                # Add the form
                review_form = StepReviewForm(initial={
                    "decided_by": request.user.id,
                    "step_state": self.step_state.id,
                })
                context["review_form"] = review_form

                # Set the default approval message
                context["review_messages"] = {}
                if self.step_state.step.review_message:
                    context["review_messages"][StepStateReview.Status.Approved.value] = self.step_state.step.review_message

        return context

    def get_cleaned_data(self, request) -> dict[str, object]:
        """
        For the given HttpRequest, finds, extracts and cleans data for persisting.
        """
        # Get data
        if hasattr(request, "data"):
            data = request.data
        elif hasattr(request, "POST"):
            data = request.POST

        # Remove request meta fields
        cleaned_data = {k:v for k, v in data.items() if k not in self.request_meta_fields()}

        # Sanitize strings
        for key, value in cleaned_data.items():
            if type(value) is str and nh3.is_html(value):
                cleaned_data[key] = nh3.clean(value)


        return cleaned_data

    def save_data(self, request) -> tuple[HTTPStatus, Optional[str | dict]]:
        """
        Accepts an HttpRequest object and extracts data to be saved for the StepState object.
        """
        self.step_state.data = self.get_cleaned_data(request)
        self.step_state.save()

        return HTTPStatus.OK, None

    def update_data(self, request) -> tuple[HTTPStatus, Optional[str | dict]]:
        """
        Accepts an HttpRequest object and extracts data to be saved for the StepState object.
        """
        # Extract and clean data
        cleaned_data = self.get_cleaned_data(request)

        # Check if exists
        if self.step_state.data:

            try:
                # Attempt to update
                self.step_state.data.update(cleaned_data)
                self.step_state.save()

            except Exception as e:
                logger.exception(e, exc_info=True)
                return HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to update data"

        return HTTPStatus.NO_CONTENT, None

    def save_file(self, request, step_state_file) -> tuple[HTTPStatus, Optional[str | dict]]:
        """
        Accepts an HttpRequest and a created StepStateFile object and handles
        how to relate it to the current StepState.
        """
        # Remove request meta fields
        cleaned_data = self.get_cleaned_data(request)

        # Check the status
        if self.is_administration and self.step_state.status == StepState.Status.Uninitialized.value:

            # Save it as an initialization.
            initialization = StepStateInitialization.objects.create(
                step_state=self.step_state,
                data=cleaned_data,
                initialized_by=request.user,
                file=step_state_file,
                message=self.step_state.step.initialization_message,
            )

            # Notify
            self.was_initialized(request, initialization)

        else:

            # Save it as a file for the StepState.
            self.step_state.file = step_state_file
            self.step_state.data = cleaned_data
            self.step_state.save()

        return HTTPStatus.CREATED, None

    def was_reviewed(self, request: HttpRequest, review: StepStateReview):
        """
        Handles a review decision.
        """
        # Check for a rejection and handle accordingly.
        if review.status == StepStateReview.Status.Rejected.value:

            # Create a version from the existing step state
            version = StepStateVersion.objects.create(
                step_state=self.step_state,
                data=self.step_state.data,
                file=self.step_state.file,
                message=review.message,
            )

            # Detach the review and add the version to it
            review.step_state = None
            review.version = version
            review.save()

            # Reset this step state
            self.step_state.reset()

        # Check for a message
        if review.message:

            # Get the DataProject
            data_project = DataProjectWorkflow.objects.get(workflow=self.step_state.step.workflow).data_project

            # Send notification to the user.
            self.send_notification(
                request=request,
                subject=f"HMS DBMI Data Portal - {data_project.name} - Update",
                message=review.message,
            )

    def was_initialized(self, request: HttpRequest, initialization: StepStateInitialization):
        """
        Handles an initialization completion.
        """
        # Check for a message
        if initialization.message:

            # Get the DataProject
            data_project = DataProjectWorkflow.objects.get(workflow=self.step_state.step.workflow).data_project

            # Send notification to the user.
            self.send_notification(
                request=request,
                subject=f"HMS DBMI Data Portal - {data_project.name} - Update",
                message=initialization.message,
            )

    def send_notification(self, request: HttpRequest, subject: str, message: str, template: str = "workflows/email/default.html") -> bool:
        """
        Sends a notification with the included message to the owner of this
        Step State and returns whether the email was sent successfully or not.
        """
        try:
            # Get the DataProject
            data_project = DataProjectWorkflow.objects.get(workflow=self.step_state.step.workflow).data_project

            # Form the context.
            context = {
                "step": self.step_state.step,
                "workflow": self.step_state.step.workflow,
                "data_project": data_project,
                "message": message,
                "data_project_url": request.build_absolute_uri(reverse("projects:view-project", kwargs={"project_key": data_project.project_key})),
            }

            # Render templates
            body_html = render_to_string(template, context)
            body = render_to_string(template.replace(".html", ".txt"), context)

            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=settings.EMAIL_FROM_ADDRESS,
                reply_to=(settings.EMAIL_REPLY_TO_ADDRESS, ),
                to=[self.step_state.user.email]
            )
            email.attach_alternative(body_html, "text/html")
            email.send()

            return True

        except Exception as e:
            logger.exception(f"Error sending request: {e}", exc_info=True)
            return False

class FormStepController(BaseStepController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "Form Step Controller"

    def template(self, request) -> str:
        """
        Returns the name of the template to be used for rendering the StepState object.
        """
        return "workflows/steps/form.html" if not self.is_administration else "workflows/admin/steps/form.html"

    def render_context(self, request) -> dict:
        """
        Returns the context to be used for rendering the StepState object.
        """
        # Get context from super
        context = super().render_context(request)

        # Build form context based on who is viewing
        if self.is_administration:
            # Build the form with data
            form = self.step_state.step.form(initial=self.step_state.data)

        else:
            # Initialize the form class
            form = self.step_state.step.form()

        # Add form
        context["form"] = form

        return context

    def save_data(self, request) -> tuple[HTTPStatus, Optional[str | dict]]:
        """
        Accepts an HttpRequest object and extracts data to be saved for the StepState object.
        """
        # Attempt to parse form data.
        form = self.step_state.step.form(request.POST)
        if not form.is_valid():
            return HTTPStatus.BAD_REQUEST, form.errors.as_json()

        # Save forms cleaned data
        self.step_state.data = form.cleaned_data
        self.step_state.save()

        return HTTPStatus.OK, None


class FileUploadStepController(BaseStepController):

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "File Upload Step Controller"

    def template(self, request) -> str:
        """
        Returns the name of the template to be used for rendering the StepState object.
        """
        return "workflows/steps/upload-file.html" if not self.is_administration else "workflows/admin/steps/upload-file.html"

    def render_context(self, request) -> dict:
        """
        Returns the context to be used for rendering the StepState object.
        """
        # Get context from super
        context = super().render_context(request)

        # Build form context based on who is viewing
        if self.is_administration:

            # Include the DataProject
            context["data_project"] = self.step_state.step.workflow.get_data_project()

        else:
            # Set initial data for the form
            initial_data = {
                "user": request.user.id,
                "step_state": self.step_state.id,
            }
            # Initialize the form class
            form = self.step_state.step.form(
                initial=initial_data,
                allowed_media_types=[m.value for m in self.step_state.step.allowed_media_types.all()]
            )

            # Add form
            context["form"] = form

        return context


class RexplainVideoStepController(BaseStepController):
    """
    Controller for managing a step in a workflow.
    """

    @classmethod
    def name(cls):
        """
        Returns the name of the controller.
        """
        return "File Upload Step Controller"

    def template(self, request) -> str:
        """
        Returns the name of the template to be used for rendering the StepState object.
        """
        return "workflows/steps/rexplain-video.html" if not self.is_administration else "workflows/admin/steps/rexplain-video.html"

    def render_context(self, request) -> dict:
        """
        Returns the context to be used for rendering the StepState object.
        """
        # Get context from super
        context = super().render_context(request)

        # Check if admin
        if self.is_administration:

            # Set allowed media types
            allowed_media_types = [
                "video/mp4",
                "video/webm",
                "video/ogg",
                "video/x-matroska",
                "video/quicktime",
                "video/x-msvideo",
                "video/x-flv",
            ]

            # Set initial data
            initial = {
                "step_state": self.step_state.id,
                "user": self.step_state.user.id,
            }

            # Initialize the form class
            form = StepStateFileForm(initial=initial, allowed_media_types=allowed_media_types)

            # Render it
            context["form"] = form

        else:

            # Check if the step has been initialized
            if self.step_state.is_initialized:

                # Set it in context
                context["video_url"] = self.step_state.initialization.file.get_download_url()

        return context

    def get_cleaned_data(self, request):

        # Check context
        if self.is_administration:
            return super().get_cleaned_data(request)

        else:
            # Get the cleaned data
            cleaned_data = super().get_cleaned_data(request)

            # Check for an update
            if cleaned_data.get("video-tracking-event"):
                return cleaned_data["video-tracking-event"]

            # Parse it
            return json.loads(cleaned_data["video-tracking"])

    def save_data(self, request) -> tuple[HTTPStatus, Optional[str | dict]]:
        """
        Accepts an HttpRequest object and extracts data to be saved for the StepState object.
        """
        # Check for valid data
        video_tracking_data = None
        try:
            # Get the video tracking object
            video_tracking_data = self.get_cleaned_data(request)

        except Exception as e:
            logger.exception(e, exc_info=True)
            return HTTPStatus.BAD_REQUEST, "'video-tracking' parameter is required must be a valid JSON object"

        self.step_state.data = video_tracking_data
        self.step_state.save()

        return HTTPStatus.OK, None

    def update_data(self, request) -> tuple[HTTPStatus, Optional[str | dict]]:
        """
        Accepts an HttpRequest object and extracts data to be updated for the StepState object.
        """
        # Check for valid data
        video_tracking_data = None
        try:
            # Get the video tracking object
            video_tracking_data = self.get_cleaned_data(request)

        except Exception as e:
            logger.exception(e, exc_info=True)
            return HTTPStatus.BAD_REQUEST, "'video-tracking' parameter is required must be a valid JSON object"

        # Check if exists
        if self.step_state.data:

            try:
                # Attempt to update
                self.step_state.data.append(video_tracking_data)
                self.step_state.save()

            except Exception as e:
                logger.exception(e, exc_info=True)
                return HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to update data"

        else:

            # Save it.
            self.step_state.data = [video_tracking_data]
            self.step_state.save()

        return HTTPStatus.OK, None
