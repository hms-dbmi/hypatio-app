from django.contrib.auth.models import User
from django.test import TestCase
from .steps.dynamic_form import SignAgreementFormsStepInitializer
from .steps.dynamic_form import save_dynamic_form

from .models import AgreementForm
from .models import PayerDBForm
from .models import AGREEMENT_FORM_TYPE_DJANGO
from .models import DataProject
from .models import Team


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
        assert steps[0].template == "projects/signup/dynamic-agreement-form.html"

    def test_submit_agreement_form(self):

        agreement_form_id = self.test_project_1.agreement_forms.first().id
        project_key = self.test_project_1.project_key
        model_name = "payerdb"

        submit_form = {
                       "name": "TEST_NAME",
                       "title": "TEST_TITLE",
                       "harvard_address": "TEST_ADDRESS",
                       "phone": "TEST_PHONE",
                       "primary_department": "TEST_PRIMARY_DEPARTMENT",
                       "specific_aims": "TEST_AIMS",
                       "number_team_access": "TEST_NUM_ACCESS",
                       "team_sql": "TEST_SQL",
                       "team_r": "TEST_R",
                       "team_orchestra": "TEST_ORCHESTRA",
                       "team_windows": "TEST_WINDOWS",
                       "team_analysis": "TEST_ANALYSIS",
                       "team_interests": "TEST_INTERESTS",
                       "funding": "TEST_FUNDING",
                       "protocol_number": "TEST_PROTOCOL_NUMBER",
                       "signature": "TEST_ID_SIGNATURE"}

        save_dynamic_form(agreement_form_id=agreement_form_id,
                          project_key=project_key,
                          model_name=model_name,
                          posted_form=submit_form,
                          user=self.super_user,
                          agreement_text="THIS IS AGREEMENT TEXT LA LA <DIV></DIV>")

        # Did we save the form okay?
        assert PayerDBForm.objects.filter(name="TEST_NAME").exists()

        # Did we create the team?
        assert Team.objects.filter(team_leader=self.super_user).exists()
