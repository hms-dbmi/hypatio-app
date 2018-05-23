from django import forms
from ..models import PayerDBForm


class AccessRequestForm(forms.ModelForm):

    class Meta:

        model = PayerDBForm
        exclude = ['user', 'agreement_form', 'project', 'date_signed', 'agreement_text', 'status']

    @property
    def render_title(self):
        return """
            <p>
        Use this form to request access to the specified HDS resource(s) provided by the Department of Biomedical
        Informatics at Harvard Medical School. <b>Applications are currently only being accepted from HMS-affiliated
        faculty members.</b> Please understand that while we will make every effort to accommodate your request for
        access, due to the large number of such requests and constrained resources, some applications may not be
        approved, or will be entered into a queue for delayed access as resources become available.
    </p>

    <p>
        Approved requests for access will automatically expire after the study duration. Please re-submit this form
        to request continuation of a prior project and provide a reference to your previous protocol in place of
        a description of the proposed work (Section 2 below). <br/>
    </p>

    <p>
        Data access requests go through a three-stage approval process. First, the study team will be evaluated for
        technical competency, second the science and related IRB approvals will be vetted by DBMI faculty, and
        finally the request will be shared with the data owner (insurance company) for their approval and any
        concomitant stipulations surrounding publication and intellectual property. <br/>
    </p>

    <p>
        Please address the following as completely as possible, and feel free to include any additional information
        that you believe may help us to evaluate your request. <br/>
    </p>

    <hr/>
        """