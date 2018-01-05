from django import forms

class UserProfileForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=255, required=True)
    last_name = forms.CharField(label='Last Name', max_length=255, required=True)
    email = forms.EmailField(label='Email', max_length=255, required=True)
    street_address1 = forms.CharField(label="Street Address 1", max_length=255, required=False)
    street_address2 = forms.CharField(label="Street Address 2", max_length=255, required=False)
    city = forms.CharField(label="City", max_length=255, required=False)
    state = forms.CharField(label="State", max_length=255, required=False)
    zipcode = forms.CharField(label="Zip", max_length=255, required=False)
    phone_number = forms.CharField(label="Phone Number", max_length=255, required=False)
