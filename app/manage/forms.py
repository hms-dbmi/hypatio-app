from django.contrib.admin.widgets import AdminDateWidget
from django.forms import ModelForm
from django.forms import DateTimeInput

from projects.models import HostedFile

# TODO:
# convert the edit-hosted-file-form to a form here
# ... figure out how to do a datetime widget, maybe use django admin's.
# convert the other forms to django forms 

class EditHostedFileForm(ModelForm):
    class Meta:
        model = HostedFile
        fields = ['long_name', 'description', 'enabled', 'opened_time', 'closed_time']

        widgets = {
            'opened_time': AdminDateWidget()
        }
