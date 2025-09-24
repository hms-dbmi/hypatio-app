from django import forms
import nh3


class SanitizedCharField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.nh3_options = kwargs.pop('nh3_options', {})
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        if value not in self.empty_values:
            value = nh3.clean(value, **self.nh3_options)
        return value
