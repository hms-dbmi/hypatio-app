from projects.models import SignedAgreementForm
from projects.models import AGREEMENT_FORM_TYPE_STATIC
from projects.models import AGREEMENT_FORM_TYPE_EXTERNAL_LINK

from projects.forms.payerdb import AccessRequestForm

from projects.models import AgreementForm
from projects.models import DataProject

from .project_step import ProjectStep
from .project_step import ProjectStepInitializer


def save_dynamic_form(agreement_form_id, project_key, model_name, posted_form, user, agreement_text):
    agreement_form = AgreementForm.objects.get(id=agreement_form_id)
    project = DataProject.objects.get(project_key=project_key)

    dynamic_form_type = agreement_form_factory(model_name)
    dynamic_form = dynamic_form_type(posted_form)
    dynamic_form_instance = dynamic_form.save(commit=False)
    dynamic_form_instance.agreement_form = agreement_form
    dynamic_form_instance.agreement_text = agreement_text
    dynamic_form_instance.user = user
    dynamic_form_instance.project = project
    dynamic_form_instance.save()


def agreement_form_factory(form_name, form_input=None):

    if form_name == "payerdb":
        return AccessRequestForm

    return None


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

            step = ProjectStep(title='Form: {name}'.format(name=form.name),
                               project=project)

            step.agreement_form = form

            if not form.type or form.type == AGREEMENT_FORM_TYPE_STATIC:
                step.template = 'projects/signup/sign-agreement-form.html'
            elif form.type == AGREEMENT_FORM_TYPE_EXTERNAL_LINK:
                step.template = 'projects/signup/sign-external-agreement-form.html'
            else:
                step.template = 'projects/signup/dynamic-agreement-form.html'
                step.form = agreement_form_factory(form.form_file_path)
                step.return_url = "projects/%s/" % project.project_key
                step.model_name = form.form_file_path

            step.status = status

            steps.append(step)

        return current_step, steps
