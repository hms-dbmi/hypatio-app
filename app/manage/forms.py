from django import forms
from django.core.validators import RegexValidator
from bootstrap_datepicker_plus import DateTimePickerInput
from dal import autocomplete

from projects.models import DataProject
from projects.models import HostedFile

# TODO Convert all other manual forms into Django forms
# ...


class EditHostedFileForm(forms.ModelForm):
    project = forms.ModelChoiceField(queryset=DataProject.objects.all(), widget=forms.HiddenInput)

    # Temporarily hidden fields for now
    file_name = forms.CharField(widget=forms.HiddenInput)
    file_location = forms.CharField(widget=forms.HiddenInput)

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
    file_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), validators=[file_name_validator])
    file_location = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), validators=[file_path_validator])

    class Meta:
        model = HostedFile
        fields = ['project', 'long_name', 'description', 'file_name', 'file_location', 'enabled', 'opened_time', 'closed_time', 'hostedfileset']
        widgets = {
            'long_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}),
            'opened_time': DateTimePickerInput(attrs={'class': 'form-control', 'placeholder': 'MM/DD/YYYY HH:MM'}).start_of('available days'),
            'closed_time': DateTimePickerInput(attrs={'class': 'form-control', 'placeholder': 'MM/DD/YYYY HH:MM'}).end_of('available days'),
            'hostedfileset': autocomplete.ModelSelect2(url='projects:hostedfileset-autocomplete', forward=['project'], attrs={'class': 'form-control form-control-select2'})
        }

