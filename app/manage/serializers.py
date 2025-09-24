from rest_framework import serializers
from django.contrib.auth.models import User

from hypatio.serializers import UserSerializer
from projects.models import DataProject
from projects.models import DataProjectWorkflow
from workflows.serializers import WorkflowStateSerializer

from workflows.serializers import WorkflowSerializer
from workflows.models import Workflow
from workflows.models import WorkflowDependency
from workflows.models import Step
from workflows.models import StepDependency
from workflows.models import WorkflowState
from workflows.models import StepState


class DataProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataProject
        fields = '__all__'
        read_only_fields = ['created', 'modified', ]


class DataProjectWorkflowSerializer(serializers.ModelSerializer):
    data_project = DataProjectSerializer(read_only=True)
    workflow = WorkflowSerializer(read_only=True)

    class Meta:
        model = DataProjectWorkflow
        fields = '__all__'
        read_only_fields = ['created', 'modified', ]


class DataProjectWorkflowStateSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    workflow = WorkflowSerializer(read_only=True)

    class Meta:
        model = WorkflowState
        fields = '__all__'
        read_only_fields = ['created_at', 'modified_at', ]