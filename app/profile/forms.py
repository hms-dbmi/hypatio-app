from django import forms
from django.utils.safestring import mark_safe

from django_countries import countries
from django_countries.fields import LazyTypedChoiceField
from django_countries.widgets import CountrySelectWidget

class RegistrationForm(forms.Form):

    ACADEMIC = 'AC'
    INDUSTRY = 'IN'
    NONE = ''

    AFFILIATION_CHOICES = (
        (ACADEMIC, 'Academic'),
        (INDUSTRY, 'Industry'),
        (NONE, 'None')
    )

    id = forms.CharField(label='ID', max_length=255, required=False, widget=forms.TextInput(attrs={'readonly':'readonly', 'type':'hidden'}))

    first_name = forms.CharField(label='First Name', max_length=255, required=True)
    last_name = forms.CharField(label='Last Name', max_length=255, required=True)
    email = forms.EmailField(label='Primary Email', max_length=255, required=True, widget=forms.TextInput(attrs={'readonly':'readonly'}))
    alternate_email = forms.EmailField(label='Alternate Email', max_length=255, required=False)

    institution = forms.CharField(label='Institution', max_length=255, required=False)
    affiliation_type = forms.ChoiceField(label='Institution Type', required=False, choices=AFFILIATION_CHOICES)
    professional_title = forms.CharField(label='Professional Title', max_length=255, required=True)

    street_address1 = forms.CharField(label="Street Address 1", max_length=255, required=False)
    street_address2 = forms.CharField(label="Street Address 2", max_length=255, initial="", required=False)
    city = forms.CharField(label="City", max_length=255, required=False)
    state = forms.CharField(label="State", max_length=255, required=False)
    zipcode = forms.CharField(label="Zip", max_length=255, required=False)
    country = LazyTypedChoiceField(choices=countries, widget=CountrySelectWidget())
    phone_number = forms.CharField(label="Phone Number", max_length=255, required=False)

    email_confirmed = forms.BooleanField(label="Email confirmed", initial=False, required=False, widget=forms.TextInput(attrs={'readonly':'readonly', 'type':'hidden'}))

    def __init__(self, *args, **kwargs):

        # Check if the new_registration argument was passed, and delete it before initializing the form
        new_registration = kwargs.get('new_registration', False)
        if 'new_registration' in kwargs:
            del kwargs['new_registration']

        super().__init__(*args, **kwargs)

        # TODO this is not working on firefox?
        # If this field already has a value, it should not be changed
        # if self.initial.get('first_name', '') != '':
        #     self.fields['first_name'].widget = forms.TextInput(attrs={'readonly':'readonly'})
        # if self.initial.get('last_name', '') != '':
        #     self.fields['last_name'].widget = forms.TextInput(attrs={'readonly':'readonly'})

        # If the email is confirmed, mark it as such on the profile
        if self.initial.get('email_confirmed', False):
            self.fields['email'].help_text = mark_safe('<div style="margin-top: 8px;"><span class="label label-success"><span class="glyphicon glyphicon-ok"></span> Verified!</span></div>')
