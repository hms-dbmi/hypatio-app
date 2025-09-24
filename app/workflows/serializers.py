from rest_framework import serializers

from hypatio.serializers import UserSerializer
from workflows.models import Workflow
from workflows.models import WorkflowDependency
from workflows.models import Step
from workflows.models import StepDependency
from workflows.models import WorkflowState
from workflows.models import StepState
from workflows.models import StepStateReview
from workflows.models import StepStateInitialization
from workflows.models import StepStateVersion
from workflows.models import StepStateFile


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class WorkflowStateSerializer(serializers.ModelSerializer):
    user = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:user-detail',
    )
    workflow = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:workflow-detail',
    )

    class Meta:
        model = WorkflowState
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class WorkflowDependencySerializer(serializers.ModelSerializer):
    workflow = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:workflow-detail',
    )
    depends_on = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:workflow-detail',
    )

    class Meta:
        model = WorkflowDependency
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class StepSerializer(serializers.ModelSerializer):
    workflow = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:workflow-detail',
    )

    class Meta:
        model = Step
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class StepStateSerializer(serializers.ModelSerializer):
    user = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:user-detail',
    )
    workflow_state = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:workflow-state-detail',
    )
    step = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-detail',
    )

    class Meta:
        model = StepState
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class StepDependencySerializer(serializers.ModelSerializer):
    step = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-detail',
    )
    depends_on = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-detail',
    )

    class Meta:
        model = StepDependency
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class StepStateReviewSerializer(serializers.ModelSerializer):
    step_state = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-state-detail',
    )

    class Meta:
        model = StepStateReview
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class StepStateInitializationSerializer(serializers.ModelSerializer):
    step_state = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-state-detail',
    )

    class Meta:
        model = StepStateInitialization
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]


class StepStateVersionSerializer(serializers.ModelSerializer):
    step_state = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-state-detail',
    )

    class Meta:
        model = StepStateVersion
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', 'version', 'data', ]


class StepStateFileSerializer(serializers.ModelSerializer):
    step_state = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflows:v1:step-state-detail',
    )

    class Meta:
        model = StepStateFile
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]
