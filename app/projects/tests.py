from django.contrib.auth.models import User
from django.test import TestCase
from .steps.dynamic_form import SignAgreementFormsStepInitializer
from .steps.dynamic_form import save_dynamic_form

from .models import AgreementForm
from .models import AGREEMENT_FORM_TYPE_DJANGO
from .models import DataProject


class AgreementFormTest(TestCase):
    def setUp(self):
        super(AgreementFormTest, self).setUp()

        self.super_user = User.objects.create_superuser('rootuser', 'rootuser@thebeatles.com', 'password')

        agreement_form1 = AgreementForm.objects.create(name="AgreementForm1",
                                                       short_name="AgreementForm1",
                                                       type=AGREEMENT_FORM_TYPE_DJANGO)

        self.test_project_1 = DataProject.objects.create(name="TEST_PROJECT_1",
                                                         project_key="TEST_1")

        self.test_project_1.agreement_forms.add(agreement_form1)

    def test_agreement_form_step(self):

        step_initializer = SignAgreementFormsStepInitializer()

        current_step, steps = step_initializer.update_context(project=self.test_project_1,
                                                                 user=self.super_user,
                                                                 current_step=None)
        assert current_step == "AgreementForm1"
        assert steps[0].template == "project_signup/dynamic_agreement_form.html"

    def test_submit_agreement_form(self):

        agreement_form_id = self.test_project_1.agreement_forms.id
        project_key = self.test_project_1.project_key
        model_name = "payerdb"
        submit_form = {"id_name":"TEST_NAME"}
        user = self.super_user

        save_dynamic_form(agreement_form_id, project_key, model_name, submit_form, user)