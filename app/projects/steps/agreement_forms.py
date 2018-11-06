from projects.models import SignedAgreementForm
from projects.models import AGREEMENT_FORM_TYPE_STATIC
from projects.models import AGREEMENT_FORM_TYPE_EXTERNAL_LINK

from projects.steps.project_step import ProjectStep
from projects.steps.project_step import ProjectStepInitializer

class SignAgreementFormsStepInitializer(ProjectStepInitializer):
    @staticmethod
    def get_step_status(current_step, step_name, form_type, step_complete):
        """
        Returns the status this step should have. If the given step is incomplete and we do not
        already have a current_step in context, then this step is the current step and update
        context to note this. If this step is incomplete but another step has already been deemed
        the current step, then this is a future step. Permanent steps are ones that should always
        be displayed as long as all prior steps are complete.
        """

        if step_complete:
            # Continue to display externally linked forms even after a user has clicked them once
            if form_type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK:
                return current_step, 'permanent_step'
            else:
                return current_step, 'completed_step'
        elif current_step is None:
            return step_name, 'current_step'
        else:
            return current_step, 'future_step'

    def update_context(self, project, user, current_step):

        steps = []

        agreement_forms = project.agreement_forms.order_by('-name')

        # Each form will be a separate step.
        for form in agreement_forms:

            # Only include Pending or Approved forms when searching.
            signed_forms = SignedAgreementForm.objects.filter(
                user=user,
                project=project,
                agreement_form=form,
                status__in=["P", "A"]
            )

            complete = signed_forms.count() > 0
            current_step, status = self.get_step_status(current_step, form.short_name, form.type, complete)

            step = ProjectStep(
                title='Form: {name}'.format(name=form.name),
                project=project
            )

            step.agreement_form = form

            if not form.type or form.type == AGREEMENT_FORM_TYPE_STATIC:
                step.template = 'projects/signup/sign-agreement-form.html'
            elif form.type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK:
                step.template = 'projects/signup/sign-external-agreement-form.html'
            else:
                # TODO
                raise Exception("Not implemented")

            step.status = status

            steps.append(step)

        return current_step, steps
