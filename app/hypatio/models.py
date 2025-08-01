from django.db import models
import nh3

from hypatio.forms import SanitizedCharField


class SanitizedTextField(models.TextField):

    def __init__(self, *args, **kwargs):
        self.nh3_options = kwargs.pop('nh3_options', {})
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': SanitizedCharField,
            'nh3_options': self.nh3_options,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            return nh3.clean(value, **self.nh3_options)
        return value
