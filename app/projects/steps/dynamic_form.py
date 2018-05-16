from abc import ABC, abstractmethod
from projects.models import SignedAgreementForm
from projects.models import AGREEMENT_FORM_TYPE_STATIC

from projects.forms.payerdb import AccessRequestForm

from projects.models import AgreementForm
from projects.models import DataProject
from projects.models import PayerDBForm

from datetime import datetime

class ProjectStep:

    template = None
    status = None
    agreement_form = None
    return_url = None
    model_name = None

    def __init__(self, title, project):
        self.title = title
        self.project = project

    def __str__(self):
        return "title : %s project : %s" % (self.title, self.project)


def save_dynamic_form(agreement_form_id, project_key, model_name, posted_form, user):
    agreement_form = AgreementForm.objects.get(id=agreement_form_id)
    project = DataProject.objects.get(project_key=project_key)

    payer_db_form_type = agreement_form_factory(model_name)

    payer_db_form = payer_db_form_type(posted_form)

    payer_db_form.save()


def agreement_form_factory(form_name, form_input=None):

    if form_name == "payerdb":
        if form_input:
            return AccessRequestForm
        else:
            return AccessRequestForm

    return None


class ProjectStepInitializer(ABC):

    @abstractmethod
    def update_context(self):
        pass


class SignAgreementFormsStepInitializer(ProjectStepInitializer):
    @staticmethod
    def get_step_status(current_step, step_name, step_complete):
        """
        Returns the status this step should have. If the given step is incomplete and we do not
        already have a current_step in context, then this step is the current step and update
        context to note this. If this step is incomplete but another step has already been deemed
        the current step, then this is a future step.
        """

        if step_complete:
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
            current_step, status = self.get_step_status(current_step, form.short_name, complete)

            step = ProjectStep(title='Form: {name}'.format(name=form.name),
                               project=project)

            step.agreement_form = form

            if not form.type or form.type == AGREEMENT_FORM_TYPE_STATIC:
                step.template = 'project_signup/sign_agreement_form.html'
            else:
                step.template = 'project_signup/dynamic_agreement_form.html'
                step.form = agreement_form_factory(form.form_file_path)
                step.return_url = "projects/%s/" % project.project_key
                step.model_name = form.form_file_path

            step.status = status

            steps.append(step)

        return current_step, steps

