from django import forms
from django.utils.safestring import mark_safe
from django_countries import countries
from django_countries.fields import LazyTypedChoiceField

from hypatio.forms import SanitizedCharField


class RegistrationForm(forms.Form):

    ACADEMIC = 'AC'
    INDUSTRY = 'IN'
    NONE = ''

    AFFILIATION_CHOICES = (
        (ACADEMIC, 'Academic'),
        (INDUSTRY, 'Industry'),
        (NONE, 'None')
    )

    email = forms.EmailField(disabled=True, label='Primary Email', max_length=255)
    first_name = SanitizedCharField(label='First Name', max_length=255, required=True)
    last_name = SanitizedCharField(label='Last Name', max_length=255, required=True)
    alternate_email = forms.EmailField(label='Alternate Email', max_length=255, required=False)

    institution = SanitizedCharField(label='Institution', max_length=255, required=False)
    affiliation_type = forms.ChoiceField(label='Institution Type', required=False, choices=AFFILIATION_CHOICES)
    professional_title = SanitizedCharField(label='Professional Title', max_length=255, required=True)

    street_address1 = SanitizedCharField(label="Street Address 1", max_length=255, required=False)
    street_address2 = SanitizedCharField(label="Street Address 2", max_length=255, initial="", required=False)
    city = SanitizedCharField(label="City", max_length=255, required=False)
    state = SanitizedCharField(label="State", max_length=255, required=False)
    zipcode = SanitizedCharField(label="Zip", max_length=255, required=False)
    country = LazyTypedChoiceField(choices=countries)
    phone_number = SanitizedCharField(label="Phone Number", max_length=255, required=False)

    def __init__(self, *args, **kwargs):

        # Set custom kwargs here
        self.new_registration = kwargs.pop('new_registration', False)
        self.email_confirmed = kwargs.pop('email_confirmed', False)

        super().__init__(*args, **kwargs)

        # If the email is confirmed, mark it as such on the profile
        if self.email_confirmed:
            self.fields['email'].help_text = mark_safe('<div class="profile-email-verified-badge-container"><span class="label label-success"><span class="glyphicon glyphicon-ok"></span> Verified!</span></div>')
