from django import forms


class HorizontalRadioSelect(forms.RadioSelect):
    template_name = 'workflows/widgets/horizontal-radio-input.html'
    option_template_name = 'workflows/widgets/horizontal-radio-option.html'
