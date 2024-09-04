from django import forms
from django.http import HttpRequest
import django.forms.fields as fields
import django.forms.widgets as widgets
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from hypatio.scireg_services import get_current_user_profile
from projects.models import DataProject, AgreementForm


class MultiValueValidationError(ValidationError):
    def __init__(self, errors):
        clean_errors = [
            f"{message} (item {key})" for message, key, value in errors
        ]
        super().__init__(clean_errors)
        self.error_detail = errors


class MultiValueFieldWidget(widgets.Input):

    def __init__(self, param_name: str) -> None:
        super().__init__()
        self.param_name: str = param_name

    def value_from_datadict(self, data, *args):
        return data.getlist(self.param_name)


class MultiValueField(fields.Field):

    def __init__(self,
                 subfield: fields.Field,
                 param_name: str,
                 *args, **kwargs) -> None:
        print(kwargs)
        super().__init__(
            widget=MultiValueFieldWidget(param_name),
            *args, **kwargs,
        )
        self.error_messages["required"] = _(
            "Please specify one or more '{}' arguments."
        ).format(param_name)
        self.subfield = subfield

    def clean(self, values):
        if len(values) == 0 and self.required:
            raise ValidationError(self.error_messages["required"])
        result = []
        errors = []
        for i, value in enumerate(values):
            try:
                result.append(self.subfield.clean(value))
            except ValidationError as e:
                if self.required:
                    errors.append((e.message, i, value))
        if len(errors):
            raise MultiValueValidationError(errors)
        return result


class AgreementFormForm(forms.Form):

    def __init__(
        self,
        request: HttpRequest,
        project: DataProject,
        agreement_form: AgreementForm,
        *args,
        **kwargs
    ):
        # Get initial data
        if not kwargs.get("initial"):
            kwargs["initial"] = self.set_initial(request, project, agreement_form)
        super().__init__(*args, **kwargs)

    def set_initial(self, request: HttpRequest, project: DataProject, agreement_form: AgreementForm) -> dict[str, object]:
        """
        Returns initial data for when the form is rendered.

        :param request: The current request
        :type request: HttpRequest
        :param project: The current data project
        :type project: DataProject
        :param agreement_form: The current agreement form this form is for
        :type agreement_form: AgreementForm
        :return: A dictionary of fields mapped to values
        :rtype: dict[str, object]
        """
        return {}

    def get_data(self, request: HttpRequest, project: DataProject, agreement_form: AgreementForm) -> dict[str, object]:
        """
        Returns the data to be set on the agreement form object.

        :param request: The request
        :type request: HttpRequest
        :param project: The data project
        :type project: DataProject
        :param agreement_form: The agreement form this form is for
        :type agreement_form: AgreementForm
        :return: A dictionary of fields mapped to values
        :rtype: dict[str, object]
        """
        return self.cleaned_data


class AgreementForm4CEDUAForm(AgreementFormForm):

    REGISTRANT_INDIVIDUAL = "individual"
    REGISTRANT_MEMBER = "member"
    REGISTRANT_OFFICIAL = "official"
    REGISTRANT_CHOICES = (
        (REGISTRANT_INDIVIDUAL, "an individual, requesting Data under this Agreement on behalf of themself"),
        (REGISTRANT_MEMBER, "an institutional member, requesting Data under this Agreement signed by a representing institutional official"),
        (REGISTRANT_OFFICIAL, "an institutional official, requesting Data under this Agreement on behalf of their institution and its agents and employees"),
    )
    registrant_is = forms.ChoiceField(label="I am a", choices=REGISTRANT_CHOICES)
    signer_name = forms.CharField(label="Name/Title", max_length=300, required=False)
    signer_phone = forms.CharField(label="Phone", max_length=300, required=False)
    signer_email = forms.CharField(label="E-mail", max_length=300, required=False)
    signer_signature = forms.CharField(label="Electronic Signature (Full Name)", max_length=300, required=False)
    date = forms.CharField(label="Date", max_length=50, required=False)
    institute_name = forms.CharField(label="Institution Name", max_length=300, required=False)
    institute_address = forms.CharField(label="Institution Address", max_length=300, required=False)
    institute_city = forms.CharField(label="Institution City", max_length=300, required=False)
    institute_state = forms.CharField(label="Institution State", max_length=300, required=False)
    institute_zip = forms.CharField(label="Institution Zip", max_length=300, required=False)
    member_emails = MultiValueField(forms.EmailField(), "member_emails", required=False)

    def clean(self):
        cleaned_data = super().clean()

        # Handle conditional requirements
        if cleaned_data.get("registrant_is") in [self.REGISTRANT_INDIVIDUAL, self.REGISTRANT_OFFICIAL]:

            # Set required fields under these conditions
            required_fields = [
                "signer_name",
                "signer_phone",
                "signer_email",
                "signer_signature",
                "date",
            ]

            # Check required fields
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "This is a required field")

        if cleaned_data.get("registrant_is") == self.REGISTRANT_OFFICIAL:

            # Set required fields under these conditions
            required_fields = [
                "institute_name",
                "institute_address",
                "institute_city",
                "institute_state",
                "institute_zip",
                "member_emails",
            ]

            # Check required fields
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "This is a required field")

    def set_initial(self, request: HttpRequest, project: DataProject, agreement_form: AgreementForm) -> dict[str, object]:
        """
        Returns initial data for when the form is rendered.

        :param request: The current request
        :type request: HttpRequest
        :param project: The current data project
        :type project: DataProject
        :param agreement_form: The current agreement form this form is for
        :type agreement_form: AgreementForm
        :return: A dictionary of fields mapped to values
        :rtype: dict[str, object]
        """
        initial = {}
        # TODO: Disabled until we get the HTML updated to use form values
        '''
        # Set initial data for this form
        user_jwt = request.COOKIES.get("DBMI_JWT", None)
        profile = next(iter(get_current_user_profile(user_jwt).get("results", [])), {})

        # Build dictionary
        initial = {
            "signer_name": f"{profile['first_name']} {profile['last_name']}",
            "signer_email": request.user.email,
            "signer_phone": profile.get("phone_number"),
            "institute_name": profile.get("institution"),
            "institute_address": profile.get("street_address1"),
            "institute_city": profile.get("city"),
            "institute_state": profile.get("state"),
            "institute_zip": profile.get("zipcode"),
            "institute_country": profile.get("country"),
        }
        '''
        return initial
