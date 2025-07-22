import uuid
import re
import importlib
import inspect
from enum import Enum
from collections import defaultdict
from collections import deque
from typing import Optional, Self
from copy import deepcopy

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import Form
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from polymorphic.models import PolymorphicModel
from dbmi_client import fileservice

from workflows.controllers.initializations import get_step_initialization_controller_choices
from workflows.controllers.review import get_step_review_controller_choices

import logging
logger = logging.getLogger(__name__)


def check_controller_class(controller_class_name) -> bool:
    """
    Utility method for ensuring a class is a valid controller class.
    """
    try:
        # Split module and class
        module_path, class_name = controller_class_name.rsplit(".", 1)

        # Import the module
        module = importlib.import_module(module_path)

        # Get the class
        cls = getattr(module, class_name)

        # Check it's actually a class
        if not inspect.isclass(cls):
            raise ValidationError(f"Invalid class name: {controller_class_name}. Ensure it is a valid Python import path to a class.")

        # Check if class is abstract
        if inspect.isabstract(cls):
            raise ValidationError(f"Invalid class name: {controller_class_name}. Specified class is abstract and cannot be used.")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        logger.exception(e, exc_info=True)
        raise ValidationError(f"Invalid class name: {controller_class_name}. Ensure it is a valid Python import path to a class.")

def get_controller_instance(controller_class_name, *args, **kwargs) -> object:
    """
    Utility method for instaniating and returning an instance of a controller
    class via its name.
    """
    try:
        # Split module and class
        module_path, class_name = controller_class_name.rsplit(".", 1)

        # Import the module
        module = importlib.import_module(module_path)

        controller = getattr(module, class_name)(*args, **kwargs)

        return controller

    except (ImportError, AttributeError, ValueError) as e:
        logger.exception(e, exc_info=True)
        raise ValidationError(f"Invalid class name: {controller_class_name}. Ensure it is a valid Python import path to a class.")


# class Project(models.Model):
#     """
#     Represents a Project that is composed of Workflows.
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255)
#     description = models.TextField(blank=True, null=True, help_text="A description of the project. This is used to provide context to users about what the project entails.")

#     # Meta
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name

#     def get_ordered_workflows(self) -> list["Workflow"]:

#         # Fetch all workflows and their dependencies for the data project
#         workflows = self.workflows.all()
#         dependencies = WorkflowDependency.objects.filter(workflow__in=workflows)

#         # Build graph
#         graph = defaultdict(list)
#         in_degree = {workflow.id: 0 for workflow in workflows}

#         for dep in dependencies:
#             graph[dep.depends_on_id].append(dep.workflow_id)
#             in_degree[dep.workflow_id] += 1

#         # Kahn's algorithm (topological sort)
#         queue = deque([workflow_id for workflow_id, deg in in_degree.items() if deg == 0])
#         step_map = {workflow.id: workflow for workflow in workflows}
#         ordered = []

#         while queue:
#             current = queue.popleft()
#             ordered.append(step_map[current])
#             for neighbor in graph[current]:
#                 in_degree[neighbor] -= 1
#                 if in_degree[neighbor] == 0:
#                     queue.append(neighbor)

#         if len(ordered) != len(workflows):
#             raise Exception("Cycle detected in workflow dependencies.")

#         return ordered

#     def get_ordered_workflow_states(self, user) -> list["WorkflowState"]:
#         """
#         Returns an ordered list of all WorkflowState objects that map to the
#         Workflow objects returned in `get_ordered_workflows`.
#         """
#         # Get workflows
#         workflows = self.get_ordered_workflows()

#         # Get workflow states
#         workflow_states = WorkflowState.objects.filter(workflow__in=workflows, user=user)

#         # Order them and return them
#         ordered_workflow_states = []
#         for workflow in workflows:

#             # Get matching workflow state
#             ordered_workflow_states.append(next((w for w in workflow_states if w.workflow == workflow), None))

#         return ordered_workflow_states

#     def get_or_create_workflow_state(self, workflow, user) -> tuple["WorkflowState", bool]:
#         """
#         Fetches or creates a WorkflowState object for the given Workflow and User.
#         Returns the WorkflowState object and a bool indicating whether it was
#         created or not.
#         """
#         # Attempt to fetch it.
#         workflow_state = next((w for w in self.get_ordered_workflow_states(user) if w is not None and w.workflow == workflow), None)
#         if not workflow_state:

#             # Create it.
#             workflow_state = WorkflowState.objects.create(
#                 workflow=workflow,
#                 user=user,
#             )

#         return workflow_state

#     def set_workflow_states(self, user) -> list["WorkflowState"]:
#         """
#         Iterates Workflows assigned to this DataProject and fetches or creates
#         each of the WorkflowState objects for the current user.
#         """
#         # Get ordered workflows
#         workflows = self.project.get_ordered_workflows()
#         if not workflows:
#             return []

#         # Keep a list
#         workflow_states = []

#         # Iterate Workflows
#         for index, workflow in enumerate(workflows):

#             # Check for a workflow state for each workflow.
#             workflow_state, created = self.project.get_or_create_workflow_state(workflow, user)
#             if created:

#                 # Determine status by checking the dependent workflows
#                 status = WorkflowState.Status.Current.value
#                 for workflow in workflow.get_dependencies():

#                     # Get the matching WorkflowState
#                     workflow_state_dependency = next((w for w in workflow_states if w.workflow == workflow), None)
#                     if workflow_state_dependency.status != WorkflowState.Status.Completed.value:
#                         status = WorkflowState.Status.Pending.value

#                 # Update it
#                 workflow_state.status = status
#                 workflow_state.started_at = timezone.now() if status == WorkflowState.Status.Current.value else None
#                 workflow_state.save()

#             # Add it
#             workflow_states.append(workflow_state)

#         return workflow_states


class Workflow(models.Model):
    """
    Represents a workflow for a DataProject. A workflow is a series of steps that users must complete.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, help_text="A description of the workflow. This is used to provide context to users about what the workflow entails.")
    controller = models.CharField(
        max_length=512,
        default='workflows.controllers.workflows.BaseWorkflowController',
        help_text="The fully-qualified class name for the workflow. This is used to determine how the workflow should be rendered and processed."
    )
    priority = models.IntegerField(default=0, help_text="Indicates the priority of this workflow. Lower numbers indicate higher priority. This is used to determine the order in which workflows are presented to users.")

    # Relationships
    #project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='workflows')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Save handler. Checks to ensure FQCN is valid before allowing a save.
        """
        # Check controller
        check_controller_class(self.controller)

        # Save if everything is ok
        super().save(*args, **kwargs)

    def get_controller(self, workflow_state, *args, **kwargs) -> "WorkflowController":
        """
        Returns a workflow controller instance for this workflow
        """
        return get_controller_instance(self.controller, workflow_state, *args, **kwargs)

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

    def get_dependencies(self) -> list[Self]:
        """
        Returns a list of Workflows this Workflow depends on.
        """
        dependencies = WorkflowDependency.objects.filter(workflow=self)
        return [d.depends_on for d in dependencies]

    def get_data_project(self) -> Optional["DataProject"]:
        """
        Returns the DataProject this Workflow belongs to, if any.
        """
        # Assuming a DataProject model exists and has a reverse relation to Workflow
        from projects.models import DataProjectWorkflow
        try:
            return DataProjectWorkflow.objects.get(workflow=self).data_project
        except DataProjectWorkflow.DoesNotExist:
            return None


class Step(PolymorphicModel):
    """
    Represents a step that users must complete for a given workflow.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, help_text="A description of the step. This is used to provide context to users about what the step entails.")
    position = models.IntegerField(null=True, blank=True)
    controller = models.CharField(
        max_length=512,
        default='workflows.controllers.steps.BaseStepController',
        help_text="The fully-qualified class name for the step. This is used to determine how the step should be rendered and processed."
    )
    indefinite = models.BooleanField(default=False, help_text="If true, this step will stay 'current' when set as such.")

    # Initialization
    initialization_required = models.BooleanField(default=False, help_text="Marks this step as needing an administrator initialization before it can be started.")
    initialization_notifications = models.BooleanField(default=True, help_text="If true, users will be notified when this step is initialized. This can be used to alert users that they can now complete the current step.")
    initialization_message = models.TextField(
        default="Your current step on the DBMI Data Portal has been initialized and is ready for you to continue.",
        help_text="The message that users will receive when the current step has been initialized. The email will also include a link for the user to return to the step.",
    )
    initialization_controller = models.CharField(
        blank=True,
        null=True,
        choices=get_step_initialization_controller_choices(),
        max_length=512,
        help_text="The fully-qualified class name for the controller that will handle the initialization process. This is used to determine how the initialization should be processed and rendered. All subclasses of 'BaseStepInitializationController' defined in 'workflows.controllers.initializations' will be listed as choices.",
    )

    # Reviews
    review_required = models.BooleanField(default=False, help_text="Marks this step as needing an administrator review before it can be completed.")
    review_controller = models.CharField(
        blank=True,
        null=True,
        choices=get_step_review_controller_choices(),
        max_length=512,
        help_text="The fully-qualified class name for the controller that will handle the review process. This is used to determine how the approval should be processed and rendered. All subclasses of 'BaseStepReviewController' defined in 'workflows.controllers.review' will be listed as choices.",
    )
    review_notifications = models.BooleanField(default=True, help_text="If true, users will be notified when this step is reviewed. This can be used to alert users that they can now proceed to the next step.")
    review_message = models.TextField(
        default="Your recently completed step on the DBMI Data Portal has been reviewed. Please return to the dashboard to check the status of the step.",
        help_text="The default message that users will receive when the current step has been reviewed. The email will also include a link for the user to return to the step.",
    )

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
        # Check controller
        check_controller_class(self.controller)

        # Check review controller
        if self.review_controller:
            check_controller_class(self.review_controller)

        # Check initialization controller
        if self.initialization_controller:
            check_controller_class(self.initialization_controller)

        super().save(*args, **kwargs)

    def get_controller(self, step_state, *args, **kwargs) -> "StepController":
        """
        Returns a step controller instance for this step
        """
        return get_controller_instance(self.controller, step_state, *args, **kwargs)

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

    def get_dependencies(self) -> list[Self]:
        """
        Returns a list of Steps this Step depends on.
        """
        dependencies = StepDependency.objects.filter(step=self)
        return [d.depends_on for d in dependencies]


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
        Current = 'current'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, *args, **kwargs):
        """
        Save handler. Ensures that the started_at time is set when the workflow is first created.
        Also updates the status of depending WorkflowStates and contained StepStates whenever
        a status is updated.
        """
        # Check if creating
        is_creating = self._state.adding

        # Check if status changed
        is_status_change = self.status != self.__original_status

        # Ensure date is set if completed
        if is_status_change and self.status == WorkflowState.Status.Completed.value and not self.completed_at:
            self.completed_at = timezone.now()

        # If this is a new workflow state, set the started_at time to now.
        if not self.started_at and self.status == self.Status.Pending.value:
            self.started_at = self.created_at

        # Process the save
        super().save(*args, **kwargs)

        # This this workflow is being created, create all step states.
        if is_creating:
            logger.debug(f"[Workflows][{self.workflow.slug()}][WorkflowState] Is creating new instance")

            # Set StepStates
            self.set_step_states()

        # Handle status change
        if is_status_change:
            logger.debug(f"[Workflows][{self.workflow.slug()}][WorkflowState] Is changing status: {self.status}")

            # Set WorkflowState statuses
            self.set_workflow_statuses()

    def get_controller(self, *args, **kwargs) -> "WorkflowController":
        """
        Returns a step controller instance for this step
        """
        return get_controller_instance(self.workflow.controller, self, *args, **kwargs)

    def get_dependencies(self) -> list[Self]:
        """
        Returns a list of WorkflowStates this WorkflowState depends on.
        """
        dependencies = [w.depends_on for w in WorkflowDependency.objects.filter(workflow=self.workflow)]
        dependency_workflow_states = WorkflowState.objects.filter(user=self.user, workflow__in=dependencies)
        return dependency_workflow_states

    def get_dependents(self) -> list[Self]:
        """
        Returns a list of WorkflowStates that depend on this WorkflowState.
        """
        dependents = [w.workflow for w in WorkflowDependency.objects.filter(depends_on=self.workflow)]
        dependent_workflow_states = WorkflowState.objects.filter(user=self.user, workflow__in=dependents)
        return dependent_workflow_states

    def get_ordered_step_states(self) -> list["StepState"]:
        """
        Returns an ordered list of all StepState objects that map to the
        Step objects returned in `Workflow.get_ordered_steps`. If a StepState
        does not exist for a Step, then None is placed in the list in that
        position.
        """
        # Get steps
        steps = self.workflow.get_ordered_steps()

        # Order them and return them
        ordered_step_states = []
        for step in steps:

            # Get matching step state
            ordered_step_states.append(
                next((s for s in self.step_states.all() if s.step == step), None)
            )

        return ordered_step_states

    def set_workflow_statuses(self):
        """
        When this WorkflowState is saved with a new status, this method will
        find depending WorkflowStates and update their status accordingly.
        """
        # Determine new status for dependent WorkflowStates
        status = WorkflowState.Status.Current if self.status == WorkflowState.Status.Completed.value else WorkflowState.Status.Pending

        # Fetch Workflows that depend on this Workflow
        for workflow_state in self.get_dependents():

            # Get other dependencies, if any.
            update = True
            for dependency in workflow_state.get_dependencies():

                # If their status differs from this new status, nothing to do.
                if dependency.status != self.status:
                    update = False
                    break

            # Update status
            if update:
                logger.debug(f"[Workflows][{workflow_state.workflow.slug()}][WorkflowState] Is changing status: {status.value}")
                workflow_state.status = status.value
                workflow_state.started_at = timezone.now() if status is WorkflowState.Status.Current else None
                workflow_state.save()

    def set_step_states(self):
        """
        Checks the current list of Steps in the corresponding Workflow to the
        existing StepState objects and ensures a StepState exists for each
        step.
        """
        logger.debug(f"[Workflows][{self.workflow.slug()}][WorkflowState] Setting StepStates")

        # Get existing Steps and StepStates
        steps = self.workflow.get_ordered_steps()
        step_states = self.get_ordered_step_states()

        # Save them
        current_step_states = deepcopy(step_states)

        # Check for None
        is_complete = True
        for index, step_state in enumerate(step_states):
            if step_state is None:

                # Create it.
                step_state = StepState.objects.create(
                    step=steps[index],
                    user=self.user,
                    workflow_state=self,
                )

                # Add it to the updated list
                current_step_states[index] = step_state

        # Determine statuses for each step state
        for step_state in current_step_states:

            # Determine status
            step_state.set_status()
            step_state.save()
            logger.debug(f"[WorkflowState/{self.id}][set_step_states] StepState/{step_state.step.slug()}/{step_state.id}: '{step_state.status}'")

            # Check if step is complete or not
            if not StepState.Status.is_final(step_state.status):
                is_complete = False

        # If this WorkflowState is not complete, update it as such.
        if self.status == WorkflowState.Status.Completed.value and not is_complete:
            self.status = WorkflowState.Status.Current.value
            self.completed_at = None
            self.save()

    def set_step_statuses(self):
        """
        Iterates this workflows step states and calculates their status.
        """
        # Track if the workflow is completed or not
        workflow_completed = True
        for step_state in self.get_ordered_step_states():

            # Get its dependencies and check their statuses
            dependencies = step_state.get_dependencies()

            # Calculate the next status
            status = step_state.get_next_status(dependencies=dependencies)

            # Compare the properties to set with the existing values
            if step_state.status != status.value:
                logger.debug(f"[WorkflowState/{self.id}][set_step_statuses] StepState/{step_state.step.slug()}/{step_state.id}: '{step_state.status}' -> '{status.value}'")

                # Save updated values
                step_state.status = status.value

                # Check if we need to set a started date.
                if status is StepState.Status.Current and not step_state.started_at:
                    step_state.started_at = timezone.now()

                # Save
                step_state.save()

            else:
                logger.debug(f"[WorkflowState/{self.id}][set_step_statuses] StepState/{step_state.step.slug()}/{step_state.id}: '{step_state.status}'")

            # If status is anything but completed or indefinite, the workflow is not completed
            workflow_completed = StepState.Status.is_final(step_state.status)

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
        Uninitialized = 'uninitialized'
        Current = 'current'
        Unreviewed = 'unreviewed'
        Completed = 'completed'
        Indefinite = 'indefinite'

        @classmethod
        def choices(cls):
            return [(key.value, key.name) for key in cls]

        @classmethod
        def is_final(cls, status) -> bool:
            """
            Returns whether the passed status represents a final status or not.
            """
            return cls(status) in [StepState.Status.Completed, StepState.Status.Indefinite]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the step was first current.")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="The date and time when the step was completed.")

    # Private
    _status = models.CharField(db_column="status", max_length=128, choices=Status.choices(), default=Status.Pending.value, help_text="The current status of the step.")
    _data = models.JSONField(db_column="data", blank=True, null=True, help_text="The data from this Step")
    _file = models.OneToOneField(db_column="file", to="StepStateFile", blank=True, null=True, on_delete=models.CASCADE, related_name="step_state")

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

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

        # Check status
        self.set_status()

    @property
    def file(self) -> "StepStateFile":
        return self._file

    @file.setter
    def file(self, value):
        self._file = value

        # Check status
        self.set_status()

    def reset(self):
        """
        Returns this Step State to a Current state.
        """
        self._data = None
        self._file = None
        self.completed_at = None
        self.save()

        # Set status
        self.set_status()

    def get_last_version(self) -> Optional["StepStateVersion"]:
        """
        Returns the most recent Version, if any.
        """
        return StepStateVersion.objects.filter(step_state=self).order_by("-version").first()

    def was_rejected(self) -> bool:
        """
        Returns whether this step state has been rejected previously.
        """
        if not self.step.review_required:
            return False

        # Get last version
        last_version = self.get_last_version()
        return last_version and last_version.review.status == StepStateReview.Status.Rejected.value


    def get_dependencies(self) -> list[Self]:
        """
        Returns a list of StepStates this step depends on.
        """
        dependencies = StepDependency.objects.filter(workflow=self.step.workflow, step=self.step)
        step_states = StepState.objects.filter(workflow_state=self.workflow_state, step__in=[dependency.depends_on for dependency in dependencies])
        return step_states

    def get_dependents(self) -> list[Self]:
        """
        Returns a list of StepStates that depend on this StepState.
        """
        dependents = [s.step for s in StepDependency.objects.filter(depends_on=self.step)]
        dependent_step_states = StepState.objects.filter(user=self.user, step__in=dependents)
        return dependent_step_states

    def set_status(self) -> Status:
        """
        Given the current state of the StepState, determine and set the next
        status, if any.
        """
        # Get next status
        status = self.get_next_status()

        # Compare
        if StepState.Status(self.status) is status:
            logger.debug(f"[StepState][{self.step.slug()}][{self.id}] Status unchanged: {status}")
            return status

        # Check if we need to set dates
        if status is StepState.Status.Current and not self.started_at:
            self.started_at = timezone.now()
        elif StepState.Status.is_final(status) and not self.completed_at:
            self.completed_at = timezone.now()

        # Save
        self.status = status.value
        logger.debug(f"[StepState][{self.step.slug()}][{self.id}] Next status: {status}")

        return status

    def get_next_status(self, dependencies: list["StepState"] = None) -> Status:
        """
        Given the current status, returns what the next status would be.
        """
        # Check dependencies, if necessary
        if dependencies and not all(StepState.Status.is_final(d.status) for d in dependencies):
            return StepState.Status.Pending

        match StepState.Status(self.status):
            case StepState.Status.Pending | StepState.Status.Uninitialized:

                # Check whether initialization is needed or not.
                if self.step.initialization_required and not self.is_initialized:
                    return StepState.Status.Uninitialized
                else:
                    return StepState.Status.Current

            case StepState.Status.Current | StepState.Status.Unreviewed:

                # First check for data or a file
                if self.data or self.file:

                    # Check whether review is needed or not.
                    if self.step.review_required and not self.is_reviewed:
                        return StepState.Status.Unreviewed

                    # Check for a rejected state, reverting back to current
                    elif self.step.review_required and self.is_rejected:
                        return StepState.Status.Current

                    # Check for an approved state, continuing to completed
                    elif self.step.review_required and self.is_approved:
                        return StepState.Status.Completed

                    # Check for an indefinite step
                    elif self.step.indefinite:
                        return StepState.Status.Indefinite

                    else:
                        return StepState.Status.Completed

                else:
                    return StepState.Status.Current

            case StepState.Status.Completed | StepState.Status.Indefinite:

                # Ensure it is initialized if needed
                if self.step.initialization_required and not self.is_initialized:
                    return StepState.Status.Uninitialized

                # Ensure it has review if needed
                elif self.step.review_required and not self.is_reviewed:
                    return StepState.Status.Unreviewed

                # Check for an indefinite step
                elif self.step.indefinite:
                    return StepState.Status.Indefinite

                else:
                    return StepState.Status.Completed

            case _:
                raise ValueError(f"Error: Unhandled status '{self.status}'")

    def validate_next_status(self) -> bool:
        """
        Accepts a proposed next status and ensures it's a valid transition.
        """
        match StepState.Status(self.status):

            case StepState.Status.Pending:

                # This should be allowed.
                return True

            case StepState.Status.Uninitialized:

                # Check whether initialization is needed or not.
                if not self.step.initialization_required or self.is_initialized:
                    return False

            case StepState.Status.Current:

                # Check whether initialization is needed or not.
                if self.step.initialization_required and not self.is_initialized:
                    return False

            case StepState.Status.Unreviewed:

                # Check whether review is needed or not.
                if not self.data or not self.step.review_required or self.is_reviewed:
                    return False

            case StepState.Status.Completed:

                # Check whether review is needed or not.
                if not self.data or (self.step.review_required and not self.is_approved) or self.step.indefinite:
                    return False

            case StepState.Status.Indefinite:

                # Check whether review is needed or not.
                if not self.data or (self.step.review_required and not self.is_approved) or not self.step.indefinite:
                    return False

            case _:
                raise ValueError(f"Error: Unhandled status '{self.status}'")

        return True

    def save(self, *args, **kwargs):
        """
        Save handler. If changing states, check workflow for dependent steps and update their status accordingly.
        """
        # Check if we are updating the status
        status_changed = self.status != self.__original_status and not self._state.adding

        # Check initialization and review requirements
        if status_changed and not self.validate_next_status():
            raise ValidationError(f"Error: status '{self.status}' is invalid for the current state of this object")

        # Process the save
        super().save(*args, **kwargs)

        # If this is a status change, update dependent steps.
        if status_changed:
            self.workflow_state.set_step_statuses()

    @property
    def is_initialized(self) -> bool:
        return hasattr(self, 'initialization') and self.initialization is not None

    @property
    def is_reviewed(self) -> bool:
        return hasattr(self, 'review') and self.review is not None

    @property
    def is_approved(self) -> bool:
        return hasattr(self, 'review') and self.review is not None and self.review.is_approved

    @property
    def is_rejected(self) -> bool:
        return hasattr(self, 'review') and self.review is not None and self.review.is_rejected

    def get_controller(self, *args, **kwargs):
        return get_controller_instance(self.step.controller, self, *args, **kwargs)

    def get_initialization_controller(self, *args, **kwargs):
        return get_controller_instance(self.step.initialization_controller, self, *args, **kwargs)

    def get_review_controller(self, *args, **kwargs):
        return get_controller_instance(self.step.review_controller, self, *args, **kwargs)


class StepStateInitialization(models.Model):
    """
    Represents the initialization of a step. This is used to track when a step was initialized.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.JSONField(blank=True, null=True, help_text="The data from this Step Initialization. This can be used to store any data that is required to initialize the step.")
    message = models.TextField(blank=True, null=True, help_text="An optional message describing the initialization of the step. This can be used to provide context or feedback on the actions made.")

    # Relationships
    step_state = models.OneToOneField(StepState, on_delete=models.CASCADE, related_name='initialization')
    initialized_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_initializations', help_text="The user who initialized the step.")
    file = models.OneToOneField("StepStateFile", blank=True, null=True, on_delete=models.CASCADE, related_name='initialization')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Save handler. Update the status of the StepState if needed.
        """
        super().save(*args, **kwargs)

        # Update StepState
        self.step_state.set_status()
        self.step_state.save()


class StepStateReview(models.Model):
    """
    Represents the review of a step. This is used to track a step's review by an administrator and whether it was approved or rejected.
    """
    class Status(Enum):
        Approved = "approved"
        Rejected = "rejected"

        @classmethod
        def choices(cls):
            return [(key.value, key.name) for key in cls]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(choices=Status.choices(), help_text="The outcome status of the review.", max_length=255)
    message = models.TextField(blank=True, null=True, help_text="An optional message describing the review of the step. This can be used to provide context or feedback on the decision made.")

    # Relationships
    step_state = models.OneToOneField(StepState, blank=True, null=True, on_delete=models.CASCADE, related_name='review')
    decided_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_reviews', help_text="The user who reviewed the step.")
    version = models.OneToOneField("StepStateVersion", blank=True, null=True, on_delete=models.CASCADE, related_name='review')

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def is_approved(self) -> bool:
        return StepStateReview.Status(self.status) is StepStateReview.Status.Approved

    @property
    def is_rejected(self) -> bool:
        return StepStateReview.Status(self.status) is StepStateReview.Status.Rejected

    def save(self, *args, **kwargs):
        """
        Save handler. Update the status of the StepState if needed.
        """
        super().save(*args, **kwargs)

        # Update StepState if attached
        if self.step_state:
            self.step_state.set_status()
            self.step_state.save()


class StepStateVersion(models.Model):
    """
    Represents a version of a StepState. This is used to track changes to a StepState over time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.IntegerField(help_text="The version number of the StepState.", editable=False)
    data = models.JSONField(blank=True, null=True, help_text="The data from this StepState at the time of this version.", editable=False)
    message = models.TextField(blank=True, null=True, help_text="An optional message describing the changes made in this version. This can be used to provide context or feedback on the changes made.")

    # Relationships
    step_state = models.ForeignKey(StepState, on_delete=models.CASCADE, related_name='versions')
    file = models.OneToOneField(to="StepStateFile", blank=True, null=True, on_delete=models.CASCADE, related_name="step_state_version")

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Ensures that the version number is incremented each time a StepStateVersion is saved.
        """
        # Check if creating
        if self._state.adding:

            # Get the last version
            last_version = self.step_state.versions.order_by('-version').first()

            # Set the version
            self.version = last_version.version + 1 if last_version else 1

            # Set data from existing step state
            self.data = self.step_state.data

        return super().save(*args, **kwargs)

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


class StepStateFile(models.Model):
    """
    Represents a file for a step.
    """
    class Provider(Enum):
        Fileservice = "fileservice"
        S3 = "s3"

        @classmethod
        def choices(cls):
            return [(key.value, key.name) for key in cls]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(choices=Provider.choices(), max_length=128, help_text="The provider that is storing the file and determines how it is accessed.")
    filename = models.CharField(max_length=512, help_text="The name of the file")
    size = models.BigIntegerField(help_text="The size of the file in bytes")
    url = models.CharField(max_length=512, help_text="The URL of the file")
    data = models.JSONField(blank=True, null=True, help_text="The data from the file upload.")
    media_type = models.CharField(max_length=512, help_text="The media type of the uploaded file.")

    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_state_files', help_text="The user who owns the file.")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_step_state_files', help_text="The user who uploaded the file for the step.")

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def get_download_url(self) -> str:
        """
        Returns a signed download URL from whatever provider is hosting the file.
        """
        match StepStateFile.Provider(self.provider):

            case StepStateFile.Provider.Fileservice:

                # Request a signed URL from Fileservice
                return fileservice.get_archivefile_download_url(self.data["uuid"])

            case StepStateFile.Provider.S3:
                pass

            case _:
                raise ValueError(f"Unhandled StepStateFile.Provider '{self.provider}'")
