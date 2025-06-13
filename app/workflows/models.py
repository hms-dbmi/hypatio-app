import uuid
import re
import importlib
import inspect
from enum import Enum
from collections import defaultdict, deque
from typing import Self

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import Form
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from polymorphic.models import PolymorphicModel

import logging
logger = logging.getLogger(__name__)


class Workflow(models.Model):
    """
    Represents a workflow for a DataProject. A workflow is a series of steps that users must complete.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, help_text="A description of the workflow. This is used to provide context to users about what the workflow entails.")
    class_name = models.CharField(
        max_length=512,
        default='workflows.workflows.WorkflowController',
        help_text="The fully-qualified class name for the workflow. This is used to determine how the workflow should be rendered and processed."
    )
    priority = models.IntegerField(default=0, help_text="Indicates the priority of this workflow. Lower numbers indicate higher priority. This is used to determine the order in which workflows are presented to users.")

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Save handler. Checks to ensure FQCN is valid before allowing a save.
        """
        try:
            # Split module and class
            module_path, class_name = self.class_name.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Get the class
            cls = getattr(module, class_name)

            # Check it's actually a class
            if not inspect.isclass(cls):
                raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")

            # Check if class is abstract
            if inspect.isabstract(cls):
                raise ValidationError(f"Invalid class name: {self.class_name}. Specified class is abstract and cannot be used.")

            super().save(*args, **kwargs)

        except (ImportError, AttributeError, ValueError):
            raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")

    def controller(self, step_state, *args, **kwargs) -> "WorkflowController":
        """
        Returns a workflow controller instance for this step
        """
        try:
            # Split module and class
            module_path, class_name = self.class_name.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Build the form
            return getattr(module, class_name)(step_state, *args, **kwargs)

        except (ImportError, AttributeError, ValueError):
            raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")

    def slug(self) -> str:
        """
        Returns a slugified version of the workflow name.
        """
        return re.sub(r'[^a-z0-9]+', '-', self.name.lower())

    def get_ordered_steps(self):
        # Fetch all steps and their dependencies for the workflow
        steps = Step.objects.filter(workflow=self).select_related('workflow')
        dependencies = StepDependency.objects.filter(step__in=steps)

        # Build graph
        graph = defaultdict(list)
        in_degree = {step.id: 0 for step in steps}

        for dep in dependencies:
            graph[dep.depends_on_id].append(dep.step_id)
            in_degree[dep.step_id] += 1

        # Kahn's algorithm (topological sort)
        queue = deque([step_id for step_id, deg in in_degree.items() if deg == 0])
        step_map = {step.id: step for step in steps}
        ordered = []

        while queue:
            current = queue.popleft()
            ordered.append(step_map[current])
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(steps):
            raise Exception("Cycle detected in step dependencies.")

        return ordered


class Step(PolymorphicModel):
    """
    Represents a step that users must complete for a given workflow.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, help_text="A description of the step. This is used to provide context to users about what the step entails.")
    position = models.IntegerField(null=True, blank=True)
    class_name = models.CharField(
        max_length=512,
        default='workflows.workflows.StepController',
        help_text="The fully-qualified class name for the step. This is used to determine how the step should be rendered and processed."
    )
    indefinite = models.BooleanField(default=False, help_text="If true, this step will stay 'current' when set as such.")

    # Relationships
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Save handler. Checks to ensure FQCN is valid before allowing a save.
        """
        try:
            # Split module and class
            module_path, class_name = self.class_name.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Get the class
            cls = getattr(module, class_name)

            # Check it's actually a class
            if not inspect.isclass(cls):
                raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")

            # Check if class is abstract
            if inspect.isabstract(cls):
                raise ValidationError(f"Invalid class name: {self.class_name}. Specified class is abstract and cannot be used.")

            super().save(*args, **kwargs)

        except (ImportError, AttributeError, ValueError):
            raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")

    def controller(self, step_state, *args, **kwargs) -> "StepController":
        """
        Returns a step controller instance for this step
        """
        try:
            # Split module and class
            module_path, class_name = self.class_name.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Build the form
            return getattr(module, class_name)(step_state, *args, **kwargs)

        except (ImportError, AttributeError, ValueError):
            raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")

    def is_ready(self) -> bool:
        """
        Returns True if all dependencies are completed.
        """
        return not self.dependencies.filter(depends_on__status__in=['pending', 'current']).exists()

    def slug(self) -> str:
        """
        Returns a slugified version of the step name.
        """
        return re.sub(r'[^a-z0-9]+', '-', self.name.lower())


class WorkflowDependency(models.Model):
    """
    This links workflows as dependencies. Each record says:
    'workflow' depends on 'depends_on'.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='dependents')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workflow', 'depends_on')

    def __str__(self):
        return f"{self.workflow.name} depends on {self.depends_on.name}"

class StepDependency(models.Model):
    """
    This links steps as dependencies. Each record says:
    'step' depends on 'depends_on'.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='step_dependencies')
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='dependents')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workflow', 'step', 'depends_on')

    def __str__(self):
        return f"{self.workflow.name}: {self.step.name} depends on {self.depends_on.name}"


class WorkflowState(models.Model):
    """
    Represents the state of a workflow for a user. This captures the data that a user has submitted for a workflow.
    """
    class Status(Enum):
        Pending = 'pending'
        Completed = 'completed'

        @classmethod
        def choices(cls):
            return [(key.value, key.name) for key in cls]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices(), default=Status.Pending.value, help_text="The current status of the workflow. This can be 'pending' or 'completed'.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the workflow was started.")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the workflow was completed.")

    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflow_states')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='workflow')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Save handler. Ensures that the started_at time is set when the workflow is first created.
        """
        # Check if creating
        is_creating = self._state.adding

        # If this is a new workflow state, set the started_at time to now.
        if not self.started_at and self.status == self.Status.Pending.value:
            self.started_at = self.created_at

        # Process the save
        super().save(*args, **kwargs)

        # This this workflow is being created, create all step states.
        if is_creating:

            # Fetch steps
            steps = self.workflow.get_ordered_steps()

            # Nothing to do if no steps
            if not steps:
                return

            # Create the first step with relevant properties.
            StepState.objects.create(
                step=steps[0],
                user=self.user,
                workflow_state=self,
                status=StepState.Status.Current.value,
                started_at=self.started_at,
            )

            # Create step states for each
            for step in steps[1:]:

                StepState.objects.create(
                    step=step,
                    user=self.user,
                    workflow_state=self,
                    status=StepState.Status.Pending.value,
                )

    def get_ordered_step_states(self) -> list[Self]:
        """
        Returns the step states in the order of the workflow steps.
        """
        # Get all step and states
        steps = self.workflow.get_ordered_steps()
        step_states = StepState.objects.filter(workflow_state=self).select_related('step')

        # Build an ordered list for the states
        ordered_step_states = []
        for step in steps:
            step_state = next((state for state in step_states if state.step.id == step.id), None)
            ordered_step_states.append(step_state)

        return ordered_step_states

    def set_step_statuses(self):
        """
        Iterates this workflows step states and calculates their status.
        """
        # Track if the workflow is completed or not
        workflow_completed = True
        for step_state in self.get_ordered_step_states():

            # Nothing to do if first step
            if not step_state.dependencies():
                logger.debug(f"[WorkflowState/{self.id}][set_step_statuses] StepState/{step_state.id} has no dependencies, continuing")
                continue
            elif step_state.status == StepState.Status.Completed.value:
                logger.debug(f"[WorkflowState/{self.id}][set_step_statuses] StepState/{step_state.id} is completed, continuing")
                continue

            # Get its dependencies and check their statuses
            dependencies = step_state.dependencies()
            dependency_statuses = [dependency.status for dependency in dependencies]

            # If all are completed, set this one to current
            if all(status == StepState.Status.Completed.value for status in dependency_statuses):
                status = StepState.Status.Current.value
                started_at = timezone.now() if not step_state.started_at else step_state.started_at

            else:
                # Set it to pending
                status = StepState.Status.Pending.value
                started_at = None

            # Compare the properties to set with the existing values
            if step_state.status != status or step_state.started_at != started_at:
                logger.debug(f"[WorkflowState/{self.id}][set_step_statuses] StepState/{step_state.id} is {status}")

                # Save updated values
                step_state.status = status
                step_state.started_at = started_at
                step_state.save()

            # If status is anything but completed, the workflow is not completed
            workflow_completed = step_state.status == StepState.Status.Completed.value

        # If workflow is completed, save it.
        if workflow_completed and self.status != WorkflowState.Status.Completed.value:
            logger.debug(f"[WorkflowState/{self.id}][set_step_statuses] Workflow state is completed")

            self.status = WorkflowState.Status.Completed.value
            self.completed_at = timezone.now()
            self.save()

class StepState(models.Model):
    """
    Represents the state of a step for a user. This captures the data that a user has submitted for a step.
    """
    class Status(Enum):
        Pending = 'pending'
        Current = 'current'
        Completed = 'completed'

        @classmethod
        def choices(cls):
            return [(key.value, key.name) for key in cls]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices(), default=Status.Pending.value, help_text="The current status of the step. This can be 'pending', 'current', or 'completed'.")
    requires_approval = models.BooleanField(default=False, help_text="Set this to true if this step requires approval before it can be marked as completed.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the step was first current.")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the step was completed.")
    approved_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the step was approved, if applicable.")
    data = models.JSONField(blank=True, null=True, help_text="The data from this Step")

    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_states')
    workflow_state = models.ForeignKey(WorkflowState, on_delete=models.CASCADE, related_name='step_states')
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='state')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def dependencies(self) -> list[Self]:
        """
        Returns a list of StepStates this step depends on.
        """
        dependencies = StepDependency.objects.filter(workflow=self.step.workflow, step=self.step)
        step_states = StepState.objects.filter(workflow_state=self.workflow_state, step__in=[dependency.depends_on for dependency in dependencies])
        return step_states

    def save(self, *args, **kwargs):
        """
        Save handler. If changing states, check workflow for dependent steps and update their status accordingly.
        """
        # Check if we are updating the status
        status_changed = self.status != self.__original_status

        # Process the save
        super().save(*args, **kwargs)

        # If this is a status change, update dependent steps.
        if status_changed:

            # Calculate new step statuses
            self.workflow_state.set_step_statuses()


class MediaType(models.Model):
    """
    Represents a media type for a file.
    """
    value = models.CharField(max_length=255, unique=True, help_text="The value of the media type.")

    def __str__(self):
        return self.value

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class FormStepMixin:
    """
    A mixin for steps that include a form.
    """
    def form(self, *args, **kwargs) -> Form:
        """
        Returns a form instance for this step, if a form class is specified.
        """
        try:
            # Split module and class
            module_path, class_name = self.form_class_name.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Build the form
            return getattr(module, class_name)(*args, **kwargs)

        except (ImportError, AttributeError, ValueError):
            raise ValidationError(f"Invalid class name: {self.class_name}. Ensure it is a valid Python import path to a class.")


class FormStep(Step, FormStepMixin):
    """
    A specialized step for handling forms.
    """
    form_class_name = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="The fully-qualified class name for the Form for the step. This is used to determine if and how a Form class will be used to render and process."
    )


class FileUploadStep(Step, FormStepMixin):
    """
    A specialized step for handling large file uploads.
    """
    form_class_name = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="The fully-qualified class name for the Form for the step. This is used to determine if and how a Form class will be used to render and process."
    )
    max_file_size = models.BigIntegerField(default=2147483647, help_text="The maximum file size allowed for this step in bytes. Default is 2GB.")
    s3_bucket = models.CharField(max_length=255, help_text="The S3 bucket where files for this step will be uploaded. Defaults to the first bucket configured in the setting `dbmi_settings.FILESERVICE_BUCKETS`.")

    # Allow users to specify the content types that are allowable for upload.
    allowed_media_types = models.ManyToManyField(
        MediaType,
        blank=True,
        help_text="The media types that are allowed for file uploads in this step. If empty, all media types are allowed."
    )


class VideoStep(Step):
    """
    A specialized step for showing a video.
    """
    video_url = models.TextField(help_text="The URL of the video to show in this step.")
    thumbnail_url = models.TextField(blank=True, null=True, help_text="An optional thumbnail URL for the video. This can be used to show a preview of the video before it is played.")
    autoplay = models.BooleanField(default=False, help_text="If true, the video will automatically start playing when the step is displayed.")
    loop = models.BooleanField(default=False, help_text="If true, the video will loop when it reaches the end.")
