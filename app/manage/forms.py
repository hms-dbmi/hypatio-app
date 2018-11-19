from django import forms

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
