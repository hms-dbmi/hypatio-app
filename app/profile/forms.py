from django import forms

class RegistrationForm(forms.Form):

    id = forms.CharField(label='ID', max_length=255, required=False, widget=forms.TextInput(attrs={'readonly':'readonly', 'type':'hidden'}))

    first_name = forms.CharField(label='First Name', max_length=255, required=True)
    last_name = forms.CharField(label='Last Name', max_length=255, required=True)
    email = forms.EmailField(label='Email', max_length=255, required=True, widget=forms.TextInput(attrs={'readonly':'readonly'}))

    street_address1 = forms.CharField(label="Street Address 1", max_length=255, required=True)
    street_address2 = forms.CharField(label="Street Address 2", max_length=255, initial="", required=False)
    city = forms.CharField(label="City", max_length=255, required=True)
    state = forms.CharField(label="State", max_length=255, required=True)
    zipcode = forms.CharField(label="Zip", max_length=255, required=True)
    phone_number = forms.CharField(label="Phone Number", max_length=255, required=True)

    twitter_handle = forms.CharField(label="Twitter Handle", max_length=255, initial="", required=False)
    email_confirmed = forms.BooleanField(label="Email confirmed", initial=False, required=False, widget=forms.TextInput(attrs={'readonly':'readonly', 'type':'hidden'}))

    def __init__(self, *args, **kwargs):

        # Check if the new_registration argument was passed, and delete it before initializing the form
        new_registration = kwargs.get('new_registration', False)
        if 'new_registration' in kwargs:
            del kwargs['new_registration']

        super().__init__(*args, **kwargs)

        # If this user already has a Registration, these fields should be readonly
        if not new_registration:
            self.fields['first_name'].widget = forms.TextInput(attrs={'readonly':'readonly'})
            self.fields['last_name'].widget = forms.TextInput(attrs={'readonly':'readonly'})
