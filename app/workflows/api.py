from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import permissions

from workflows.models import Workflow
from workflows.models import WorkflowDependency
from workflows.models import Step
from workflows.models import StepDependency
from workflows.models import WorkflowState
from workflows.models import StepState
from workflows.models import StepStateVersion
from hypatio.serializers import UserSerializer
from workflows.serializers import WorkflowSerializer
from workflows.serializers import StepSerializer
from workflows.serializers import WorkflowStateSerializer
from workflows.serializers import StepStateSerializer
from workflows.serializers import StepStateReviewSerializer
from workflows.serializers import StepStateInitializationSerializer
from workflows.serializers import StepStateVersionSerializer


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
    serializer_class = WorkflowStateSerializer
    permission_classes = [permissions.IsAdminUser]

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


class StepStateViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing Step states.
    """
    serializer_class = StepStateSerializer
    permission_classes = [permissions.IsAdminUser]

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

        return StepState.objects.filter(filter_conditions).distinct().select_related('step', 'workflow_state', 'user')

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

    @action(detail=True, methods=['get'])
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
            serializer.save(step_state=step_state)
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
            serializer.save(step_state=step_state)
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

    @action(detail=True, methods=['get'])
    def file(self, request, pk=None):
        """
        Retrieve a file for a specific step state.
        """
        step_state = self.get_object()
        files = StepStateFile.objects.filter(step_state=step_state)
        serializer = WorkflowStateSerializer(workflow_state_dependents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
