from copy import copy
from http import HTTPStatus

from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import status
from dbmi_client import fileservice

from workflows.permissions import IsWorkflowStateOwnerOrDataProjectAdministrator
from workflows.permissions import IsStepStateOwnerOrDataProjectAdministrator
from workflows import permissions as workflow_permissions
from workflows.models import Workflow
from workflows.models import WorkflowDependency
from workflows.models import Step
from workflows.models import StepDependency
from workflows.models import WorkflowState
from workflows.models import StepState
from workflows.models import StepStateVersion
from workflows.models import StepStateFile
from hypatio.serializers import UserSerializer
from workflows.serializers import WorkflowSerializer
from workflows.serializers import StepSerializer
from workflows.serializers import WorkflowStateSerializer
from workflows.serializers import StepStateSerializer
from workflows.serializers import StepStateReviewSerializer
from workflows.serializers import StepStateInitializationSerializer
from workflows.serializers import StepStateVersionSerializer
from workflows.serializers import StepStateFileSerializer
from workflows.forms import StepStateFileForm

import logging
logger = logging.getLogger(__name__)

# Permission sets
WORKFLOW_READONLY_PERMISSION_SET = (workflow_permissions.ReadOnly & workflow_permissions.IsOwner) | workflow_permissions.IsAdministrator
WORKFLOW_READANDWRITEONLY_PERMISSION_SET = (workflow_permissions.ReadAndWriteOnly & workflow_permissions.IsOwner) | workflow_permissions.IsAdministrator

class PartialTemplateHTMLRenderer(renderers.TemplateHTMLRenderer):
    media_type = 'text/html'
    format = 'html'


class WorkflowUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A simple ViewSet for viewing and editing Workflow users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        # Optionally filter by email
        email = self.request.query_params.get('email', None)
        if email is not None:
            return User.objects.filter(email=email)
        return super().get_queryset()


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing Workflows.
    """
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['get'])
    def dependencies(self, request, pk=None):
        """
        Retrieve dependencies for a specific workflow.
        """
        workflow = self.get_object()
        dependencies = WorkflowDependency.objects.filter(workflow=workflow)
        serializer = WorkflowSerializer([d.depends_on for d in dependencies], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def dependents(self, request, pk=None):
        """
        Retrieve dependents for a specific workflow.
        """
        workflow = self.get_object()
        dependents = WorkflowDependency.objects.filter(depends_on=workflow)
        serializer = WorkflowSerializer([d.workflow for d in dependents], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkflowStateViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing Workflow states.
    """
    renderer_classes = [PartialTemplateHTMLRenderer, renderers.TemplateHTMLRenderer, renderers.JSONRenderer, ]
    serializer_class = WorkflowStateSerializer
    permission_classes = [WORKFLOW_READONLY_PERMISSION_SET]

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        super().initial(request, *args, **kwargs)

        # Check if administration
        self.is_administration = self.basename.startswith("admin-")

    def get_queryset(self):

        # Setup the filter
        filter_conditions = Q()

        # Check for filtering based on user
        user = self.request.query_params.get('user', None)
        if user is not None:
            filter_conditions &= Q(user__id=user)

        # Check for filtering based on workflow
        workflow = self.request.query_params.get('workflow', None)
        if workflow is not None:
            filter_conditions &= Q(workflow__id=workflow)

        # Check for filtering based on status
        status = self.request.query_params.get('status', None)
        if status is not None:
            filter_conditions &= Q(status=status)

        # Check for filtering based on initialization state
        initialization_required = self.request.query_params.get('initialization_required', None)
        if initialization_required is not None and initialization_required.lower() == 'true':

            # Find all step states that need initialization.
            step_states = StepState.objects.filter(
                _status=StepState.Status.Uninitialized.value,
                step__initialization_required=True,
                initialization__isnull=True
            ).distinct()

            # Filter off those
            filter_conditions &= Q(id__in=step_states.values_list('workflow_state__id', flat=True))

        # Check for filtering based on approval state
        review_required = self.request.query_params.get('review_required', None)
        if review_required is not None and review_required.lower() == 'true':

            # Find all step states that need approval.
            step_states = StepState.objects.filter(
                _status=StepState.Status.Unreviewed.value,
                step__review_required=True,
                review__isnull=True,
            ).distinct()

            # Filter off those
            filter_conditions &= Q(id__in=step_states.values_list('workflow_state__id', flat=True))

        return WorkflowState.objects.filter(filter_conditions).distinct().select_related('workflow', 'user')

    def retrieve(self, request, *args, **kwargs):

        if request.accepted_renderer.format in ['html-partial', 'html']:

            # Get the requested object.
            workflow_state = self.get_object()

            # Check if this is an administration request
            is_administration = self.basename.startswith("admin-")

            # Initialize the controller for the workflow
            controller = workflow_state.workflow.get_controller(workflow_state, is_administration)

            # Build response elements
            context = controller.render_context(request)
            template = controller.template(request)

            # Render the response
            return Response(context, template_name=template)

        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def dependencies(self, request, pk=None):
        """
        Retrieve dependencies for a specific workflow state.
        """
        workflow = self.get_object()
        dependencies = WorkflowDependency.objects.filter(workflow=workflow)
        workflow_state_dependencies = WorkflowState.objects.filter(step__in=[d.depends_on for d in dependencies])
        serializer = WorkflowStateSerializer(workflow_state_dependencies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def dependents(self, request, pk=None):
        """
        Retrieve dependents for a specific workflow state.
        """
        workflow = self.get_object()
        dependents = StepDependency.objects.filter(depends_on=workflow)
        workflow_state_dependents = WorkflowState.objects.filter(step__in=[d.workflow for d in dependents])
        serializer = WorkflowStateSerializer(workflow_state_dependents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StepViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing Steps.
    """
    serializer_class = StepSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):

        # Setup the filter
        filter_conditions = Q()

        # Check for filtering based on workflow state
        workflow = self.request.query_params.get('workflow', None)
        if workflow is not None:
            filter_conditions &= Q(workflow__id=workflow)

        # Check for filtering based on initialization state
        initialization_required = self.request.query_params.get('initialization_required', None)
        if initialization_required is not None and initialization_required.lower() == 'true':
            filter_conditions &= Q(initialization_required=True)

        # Check for filtering based on approval state
        review_required = self.request.query_params.get('review_required', None)
        if review_required is not None and review_required.lower() == 'true':
            filter_conditions &= Q(review_required=True)

        return Step.objects.filter(filter_conditions).select_related('workflow')

    @action(detail=True, methods=['get'])
    def dependencies(self, request, pk=None):
        """
        Retrieve dependencies for a specific step.
        """
        step = self.get_object()
        dependencies = StepDependency.objects.filter(step=step)
        serializer = StepSerializer([d.depends_on for d in dependencies], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def dependents(self, request, pk=None):
        """
        Retrieve dependents for a specific step.
        """
        step = self.get_object()
        dependents = StepDependency.objects.filter(depends_on=step)
        serializer = StepSerializer([d.step for d in dependents], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StepStateViewSet(viewsets.GenericViewSet):
    """
    A simple ViewSet for viewing and editing Step states.
    """
    renderer_classes = [PartialTemplateHTMLRenderer, renderers.TemplateHTMLRenderer, renderers.JSONRenderer, ]
    serializer_class = StepStateSerializer
    permission_classes = [WORKFLOW_READONLY_PERMISSION_SET]

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        super().initial(request, *args, **kwargs)

        # Check if administration
        self.is_administration = self.basename.startswith("admin-")

    def get_queryset(self):

        # Setup the filter
        filter_conditions = Q()

        # Check for filtering based on user
        user = self.request.query_params.get('user', None)
        if user is not None:
            filter_conditions &= Q(user__id=user)

        # Check for filtering based on workflow state
        workflow = self.request.query_params.get('workflow', None)
        if workflow is not None:
            filter_conditions &= Q(workflow_state__workflow__id=workflow)

        # Check for filtering based on workflow state
        workflow_state = self.request.query_params.get('workflow-state', None)
        if workflow_state is not None:
            filter_conditions &= Q(workflow_state__id=workflow_state)

        # Check for filtering based on workflow state
        step = self.request.query_params.get('step', None)
        if step is not None:
            filter_conditions &= Q(step__id=step)

        # Check for filtering based on status
        status = self.request.query_params.get('status', None)
        if status is not None:
            filter_conditions &= Q(status=status)

        # Check for filtering based on initialization state
        initialization_required = self.request.query_params.get('initialization_required', None)
        if initialization_required is not None and initialization_required.lower() == 'true':
            filter_conditions &= Q(step__initialization_required=True)
            filter_conditions &= Q(initialization__isnull=True)

        # Check for filtering based on approval state
        review_required = self.request.query_params.get('review_required', None)
        if review_required is not None and review_required.lower() == 'true':
            filter_conditions &= Q(step__review_required=True)
            filter_conditions &= Q(review__isnull=True)

        return StepState.objects.filter(filter_conditions).distinct()

    def retrieve(self, request, *args, **kwargs):

        # Check if rendering a template
        if request.accepted_renderer.format in ['html-partial', 'html']:

            # Get the requested object.
            step_state = self.get_object()

            # Check if this is an administration request
            is_administration = self.basename.startswith("admin-")

            # Initialize the controller for the step
            controller = step_state.step.get_controller(step_state, is_administration)

            # Build response elements
            context = controller.render_context(request)
            template = controller.template(request)

            # Render the response
            return Response(context, template_name=template)

        return super().retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['post'],
        renderer_classes=[renderers.JSONRenderer],
        permission_classes=[WORKFLOW_READANDWRITEONLY_PERMISSION_SET]
    )
    def data(self, request, pk=None):
        """
        Sets data for a specific step state.
        """
        # Get the requested object.
        step_state = self.get_object()

        # Initialize the controller for the step
        controller = step_state.step.get_controller(step_state, self.is_administration)

        # Persist data
        status_code, content = controller.save_data(request)

        return Response(content, status=status_code)

    @data.mapping.patch
    def update_data(self, request, pk=None):
        """
        Update data for a specific step state.
        """
        # Get the requested object.
        step_state = self.get_object()

        # Initialize the controller for the step
        controller = step_state.step.get_controller(step_state, self.is_administration)

        # Persist data
        status_code, content = controller.update_data(request)

        return Response(content, status=status_code)

    @action(
        detail=True,
        methods=['post'],
        renderer_classes=[renderers.JSONRenderer],
        permission_classes=[WORKFLOW_READANDWRITEONLY_PERMISSION_SET]
    )
    def file(self, request, pk=None):
        """
        Managed upload of a file for a specific step state.
        """
        # Get the requested object.
        step_state = self.get_object()

        # Build the form.
        form = StepStateFileForm(request.data)
        if not form.is_valid():
            return Response(form.errors.as_json(), status=status.HTTP_400_BAD_REQUEST)

        # Fetch needed details
        filename = form.cleaned_data["filename"]

        # Prepare the metadata.
        metadata = {
            'uploader': request.user.email,
            'workflow': step_state.step.workflow.slug(),
            'workflow-state': str(step_state.workflow_state),
            'step': step_state.step.slug(),
            'step-state': str(step_state.id),
            'type': 'step-state-file-upload',
            'app': 'hypatio',
        }

        # Set tags
        tags = ["hypatio", "dbmi-portal", "step-state-file", "workflows", ]

        # Create a new record in fileservice for this file and get back information on where it should live in S3.
        uuid, upload = fileservice.create_archivefile_upload(filename, metadata, tags)

        # Form the data for the File object.
        file = {'uuid': uuid, 'location': upload['locationid'], 'filename': filename}
        data = {
            'post': upload['post'],
            'file': file,
        }

        return Response(data, status=status.HTTP_201_CREATED)

    @file.mapping.patch
    def update_file(self, request, pk=None):

        # Validate data
        if not request.data.get("filename"):
            return Response("'flename' parameter is required", status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get("size"):
            return Response("'size' parameter is required", status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get("type"):
            return Response("'type' parameter is required", status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get("uuid"):
            return Response("'uuid' parameter is required", status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get("location"):
            return Response("'location' parameter is required", status=status.HTTP_400_BAD_REQUEST)

        # Get the requested object.
        step_state = self.get_object()

        # Initialize the controller for the step
        controller = step_state.step.get_controller(step_state, self.is_administration)

        try:
            # Make the request to FileService.
            if not fileservice.uploaded_archivefile(request.data['uuid'], request.data['location']):
                logger.error('Fileservice uploadCompleted failed')
            else:
                logger.debug('Fileservice uploadCompleted succeeded')

                # Set the URL
                url = fileservice.get_archivefile_url(request.data["uuid"])

                step_state_file = StepStateFile.objects.create(
                    user=step_state.user,
                    provider=StepStateFile.Provider.Fileservice.value,
                    uploaded_by=request.user,
                    filename=request.data["filename"],
                    size=request.data["size"],
                    media_type=request.data["type"],
                    url=url,
                    data=request.data,
                )

                # Send it to the controller to manage
                controller.save_file(request, step_state_file)

            return Response(status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e, exc_info=True)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def dependencies(self, request, pk=None):
        """
        Retrieve dependencies for a specific step state.
        """
        step_state = self.get_object()
        dependencies = StepDependency.objects.filter(step=step_state.step)
        step_state_dependencies = StepState.objects.filter(step__in=[d.depends_on for d in dependencies])
        serializer = StepStateSerializer(step_state_dependencies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def dependents(self, request, pk=None):
        """
        Retrieve dependents for a specific step state.
        """
        step_state = self.get_object()
        dependents = StepDependency.objects.filter(depends_on=step_state.step)
        step_state_dependents = StepState.objects.filter(step__in=[d.step for d in dependents])
        serializer = StepStateSerializer(step_state_dependents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], renderer_classes=[renderers.JSONRenderer])
    def review(self, request, pk=None):
        """
        Retrieve the review object for a specific step state.
        """
        step_state = self.get_object()
        if hasattr(step_state, 'review'):
            serializer = StepStateReviewSerializer(step_state.review)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

    @review.mapping.post
    def create_review(self, request, pk=None):
        """
        Create a new review for a specific step state.
        """
        step_state = self.get_object()
        serializer = StepStateReviewSerializer(context={'request': request}, data=request.data)

        if serializer.is_valid():
            review = serializer.save(step_state=step_state)

            # Let the controller handle the post-review processes
            controller = step_state.step.get_controller(step_state, self.is_administration)
            controller.was_reviewed(request, review)

            # Return response
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def initialization(self, request, pk=None):
        """
        Retrieve the initialization object for a specific step state.
        """
        step_state = self.get_object()
        if hasattr(step_state, 'initialization'):
            serializer = StepStateInitializationSerializer(step_state.initialization)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Initialization not found."}, status=status.HTTP_404_NOT_FOUND)

    @initialization.mapping.post
    def create_initialization(self, request, pk=None):
        """
        Create a new initialization for a specific step state.
        """
        step_state = self.get_object()
        serializer = StepStateInitializationSerializer(data=request.data)

        if serializer.is_valid():
            initialization = serializer.save(step_state=step_state)

            # Let the controller handle the post-initialization processes
            controller = step_state.step.get_controller(step_state, self.is_administration)
            controller.was_initialized(request, initialization)

            # Return response
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Retrieve all versions for a specific step state.
        """
        step_state = self.get_object()
        versions = step_state.versions.all()
        serializer = StepStateVersionSerializer(versions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @versions.mapping.post
    def create_version(self, request, pk=None):
        """
        Create a new version for a specific step state.
        """
        step_state = self.get_object()
        serializer = StepStateVersionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(step_state=step_state)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StepStateFileViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing Step state files.
    """
    renderer_classes = [renderers.JSONRenderer, ]
    serializer_class = StepStateFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        super().initial(request, *args, **kwargs)

        # Check if administration
        self.is_administration = self.basename.startswith("admin-")

    def get_queryset(self):

        # Setup the filter
        filter_conditions = Q()

        # Check for filtering based on user
        user = self.request.query_params.get('user', None)
        if user is not None:
            filter_conditions &= Q(user__id=user)

        # Check for filtering based on step state
        step_state = self.request.query_params.get('step_state', None)
        if step_state is not None:
            filter_conditions &= Q(step_state__id=step_state)

        # Restrict to current user if not administration
        if not self.is_administration:
            filter_conditions &= Q(user=self.request.user)

        return StepStateFile.objects.filter(filter_conditions)

    def create(self, request, *args, **kwargs):

        # Determine the step state
        step_state = get_object_or_404(StepState, id=request.data.get("step_state"))

        # Build the form.
        form = step_state.step.form(request.data)
        if not form.is_valid():
            return Response(form.errors.as_json(), status=status.HTTP_400_BAD_REQUEST)

        # Create the file object
        StepStateFile.objects.create(
            uploaded_by=form.cleaned_data["user"],
            step_state=step_state,
            filename=form.cleaned_data["filename"],
            size=form.cleaned_data["size"],
        )

        return super().create(request, *args, **kwargs)
