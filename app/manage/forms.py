from django import forms
from django.core.validators import RegexValidator
from bootstrap_datepicker_plus.widgets import DateTimePickerInput
from dal import autocomplete

from hypatio.forms import SanitizedCharField
from projects.models import AgreementForm, DataProject
from projects.models import HostedFile
from projects.models import Team
from projects.models import AGREEMENT_FORM_TYPE_FILE

# TODO Convert all other manual forms into Django forms
# ...


class EditHostedFileForm(forms.ModelForm):
    project = forms.ModelChoiceField(queryset=DataProject.objects.all(), widget=forms.HiddenInput)

    # Temporarily hidden fields for now
    file_name = SanitizedCharField(widget=forms.HiddenInput)
    file_location = SanitizedCharField(widget=forms.HiddenInput)

    class Meta:
        model = HostedFile
        fields = ['project', 'long_name', 'description', 'file_name', 'file_location', 'enabled', 'opened_time', 'closed_time']
        widgets = {
            'long_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}),
            'opened_time': forms.DateTimeInput(attrs={'class': 'form-control', 'placeholder': 'MM/DD/YYYY HH:MM'}),
            'closed_time': forms.DateTimeInput(attrs={'class': 'form-control', 'placeholder': 'MM/DD/YYYY HH:MM'}),
        }


file_path_validator = RegexValidator(
    r'^[^\s]+$',
    'No spaces allowed',
    code='invalid_file_path')

file_name_validator = RegexValidator(
    r'^[^\s]+$',
    'No spaces allowed',
    code='invalid_file_path')


class HostSubmissionForm(forms.ModelForm):
    project = forms.ModelChoiceField(queryset=DataProject.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    file_name = SanitizedCharField(widget=forms.TextInput(attrs={'class': 'form-control'}), validators=[file_name_validator])
    file_location = SanitizedCharField(widget=forms.TextInput(attrs={'class': 'form-control'}), validators=[file_path_validator])

    class Meta:
        model = HostedFile
        fields = ['project', 'long_name', 'description', 'file_name', 'file_location', 'enabled', 'opened_time', 'closed_time', 'hostedfileset']
        widgets = {
            'long_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}),
            'opened_time': DateTimePickerInput(attrs={'class': 'form-control', 'placeholder': 'MM/DD/YYYY HH:MM'}),
            'closed_time': DateTimePickerInput(attrs={'class': 'form-control', 'placeholder': 'MM/DD/YYYY HH:MM'}, range_from='opened_time'),
            'hostedfileset': autocomplete.ModelSelect2(url='projects:hostedfileset-autocomplete', forward=['project'], attrs={'class': 'form-control form-control-select2'})
        }

class NotificationForm(forms.Form):
    """
    Determines the fields that will appear.
    """
    project = forms.ModelChoiceField(queryset=DataProject.objects.all(), widget=forms.HiddenInput)
    message = SanitizedCharField(label='Message', required=True, widget=forms.Textarea)
    team = forms.ModelChoiceField(queryset=Team.objects.all(), widget=forms.HiddenInput)


class UploadSignedAgreementFormForm(forms.Form):
    agreement_form = forms.ModelChoiceField(queryset=AgreementForm.objects.filter(type=AGREEMENT_FORM_TYPE_FILE, internal=True), widget=forms.Select(attrs={'class': 'form-control'}))
    project_key = SanitizedCharField(label='Project Key', max_length=128, required=True, widget=forms.HiddenInput())
    participant = SanitizedCharField(label='Participant', max_length=128, required=True, widget=forms.HiddenInput())
    signed_agreement_form = forms.FileField(label="Signed Agreement Form PDF", required=True)

    def __init__(self, *args, **kwargs):
            project_key = kwargs.pop('project_key', None)
            super(UploadSignedAgreementFormForm, self).__init__(*args, **kwargs)

            # Limit agreement form choices to those related to the passed project
            if project_key:
                self.fields['agreement_form'].queryset = DataProject.objects.get(project_key=project_key).agreement_forms.all()


class UploadSignedAgreementFormFileForm(forms.Form):
    file = forms.FileField(label="Signed Agreement Form PDF", required=True)
