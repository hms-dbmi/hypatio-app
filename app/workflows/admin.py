from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin

from workflows.models import Workflow, Step, StepDependency, WorkflowState, StepState, MediaType, FormStep, VideoStep, FileUploadStep


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_name', 'priority', 'created_at', 'modified_at', )
    readonly_fields = ('created_at', 'modified_at', )


@admin.register(Step)
class StepAdmin(PolymorphicParentModelAdmin):
    list_display = ('name', 'class_name', 'workflow', 'created_at', 'modified_at', )
    readonly_fields = ('created_at', 'modified_at', )

    # Set parent model
    base_class = Step

    # Set derived models
    child_models = (FormStep, VideoStep, FileUploadStep, )


@admin.register(StepDependency)
class StepDependencyAdmin(admin.ModelAdmin):
    list_display = ('step', 'depends_on', 'created_at', 'modified_at', )
    readonly_fields = ('created_at', 'modified_at', )


@admin.register(WorkflowState)
class WorkflowStateAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'workflow', 'started_at', 'completed_at', 'created_at', 'modified_at', )
    readonly_fields = ('started_at', 'completed_at', 'created_at', 'modified_at', )


@admin.register(StepState)
class StepStateAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'started_at', 'completed_at', 'created_at', 'modified_at', )
    readonly_fields = ('started_at', 'completed_at', 'created_at', 'modified_at', )


@admin.register(MediaType)
class MediaTypeAdmin(admin.ModelAdmin):
    list_display = ('value', 'created_at', 'modified_at', )
    readonly_fields = ('created_at', 'modified_at', )


@admin.register(FormStep)
class FormStepAdmin(PolymorphicChildModelAdmin):

    # Set parent model
    base_class = Step


@admin.register(FileUploadStep)
class FileUploadStepAdmin(PolymorphicChildModelAdmin):

    # Set parent model
    base_class = Step


@admin.register(VideoStep)
class VideoStepAdmin(PolymorphicChildModelAdmin):

    # Set parent model
    base_class = Step
