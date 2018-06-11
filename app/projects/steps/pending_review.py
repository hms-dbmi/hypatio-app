from .project_step import ProjectStepInitializer
from .project_step import ProjectStep


class PendingReviewStepInitializer(ProjectStepInitializer):
    def update_context(self, project, context):

        status = self.get_step_status(context, "pending_review", False)

        step = ProjectStep(title='Pending Review',
                           project=project,)
        step.template = 'project_signup/pending_review.html'
        step.status = status

        return step
