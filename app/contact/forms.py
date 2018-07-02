from django import forms

from projects.models import DataProject

class ProjectModelChoiceField(forms.ModelChoiceField):
    """
    A custom ModelChoiceField class in order to customize the select name that
    appears in the form. Assumes the object is a DataProject.
    """

    def label_from_instance(self, obj):
        return obj.name

class ContactForm(forms.Form):
    """
    Determines the fields that will appear.
    """

    name = forms.CharField(label='Name', max_length=255, required=True)

    email = forms.EmailField(label='Your email', max_length=255, required=True)

    project = ProjectModelChoiceField(
        label='In regards to',
        queryset=DataProject.objects.filter(visible=True),
        widget=forms.Select(
            attrs={
                'class': 'form-control',
                'selected': '',
            }
        ),
        required=False)

    message = forms.CharField(label='Question or comment', required=True, widget=forms.Textarea)
