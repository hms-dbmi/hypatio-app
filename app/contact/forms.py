from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(label='Name', max_length=255, required=True)
    email = forms.EmailField(label='Email', max_length=255, required=True)
    message = forms.CharField(label='Comment', required=True, widget=forms.Textarea)
