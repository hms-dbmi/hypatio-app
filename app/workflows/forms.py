from typing import Optional

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, HTML

from hypatio.forms import SanitizedCharField
from workflows.models import StepStateReview
from workflows.widgets import HorizontalRadioSelect
from workflows.models import MediaType


class StepReviewForm(forms.Form):
    """
    A form for reviewing a step in a workflow.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

    status = forms.ChoiceField(
        label=_("Decision"),
        help_text=_("Please select the outcome of this review"),
        choices=StepStateReview.Status.choices(),
    )
    message = SanitizedCharField(
        label="Message",
        required=False,
        widget=forms.Textarea,
        help_text="Optional message to the user to provide context or feedback on your decision (leaving blank will only send notifications if one is configured by default)"
    )
    step_state = SanitizedCharField(
        widget=forms.HiddenInput,
    )
    decided_by = SanitizedCharField(
        widget=forms.HiddenInput,
    )

class StepStateFileForm(forms.Form):
    """
    A form for uploading files.
    This form is used to test file upload functionality in workflows.
    """
    def __init__(self, *args, allowed_media_types: Optional[list[MediaType]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

        # Set allowed media types
        if not allowed_media_types:
            allowed_media_types = []

        # Update file widget
        self.fields['file'].widget.attrs.update({
            "accept": ",".join([m.value for m in allowed_media_types])
        })

        # Update help message
        if allowed_media_types:
            allowed_media_types_help = MediaType.media_types_summary(allowed_media_types)
            if allowed_media_types_help:
                self.fields['file'].help_text += f" (only {allowed_media_types_help} files are allowed)"


    user = SanitizedCharField(
        widget=forms.HiddenInput,
    )
    step_state = SanitizedCharField(
        widget=forms.HiddenInput,
    )
    file = forms.FileField(
        label="Upload a file",
        help_text="Select the file to be uploaded",
        widget=forms.ClearableFileInput(),
        required=False,
    )
    filename = SanitizedCharField(
        widget=forms.HiddenInput,
    )
    size = SanitizedCharField(
        widget=forms.HiddenInput,
    )
    type = SanitizedCharField(
        widget=forms.HiddenInput,
    )


class RexplainVideoUploadForm(forms.Form):
    """
    A form for uploading a video file.
    This form is used for admins to upload videos for users in the Rexplain project.
    """
    file = forms.FileField(
        label="Upload a video for the user",
        help_text="Please upload a file.",
        widget=forms.ClearableFileInput(attrs={'data-content-type': "video/mp4"}),
    )
    filename = SanitizedCharField(
        label="The name of the file to be uploaded",
        widget=forms.HiddenInput(),
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("No file uploaded.")
        return file


class LikertField(forms.ChoiceField):
    """
    A custom field for Likert scale responses.
    This field is used to create a horizontal radio select widget for Likert scale questions.
    """
    def __init__(self, *args, scale=5, **kwargs):

        # Set choices on a scale of 1-5 by default if not provided
        if not kwargs.get("choices"):
            kwargs["choices"] = [(i, str(i)) for i in range(1, scale + 1)]

        # Set the widget to HorizontalRadioSelect
        if not kwargs.get("widget"):
            kwargs["widget"] = HorizontalRadioSelect()

        # Pop labels
        self.left_label = kwargs.pop("left_label", None)
        self.right_label = kwargs.pop("right_label", None)

        super().__init__(*args, **kwargs)

class CrispyLikertField(Field):
    """
    A crispy field for Likert scale responses.
    This field is used to create a horizontal radio select widget for Likert scale questions.
    """
    template = 'maida-forms/likertfield.html'

    def __init__(self, *fields, css_class=None, wrapper_class=None, template=None, left_label=None, right_label=None, **kwargs):
        super().__init__(*fields, css_class=css_class, wrapper_class=wrapper_class, template=template, **kwargs)
        self.left_label = left_label
        self.right_label = right_label

    def render(self, *args, **kwargs):

        # Get labels from fields
        form = args[0]
        field = form.fields.get(self.fields[0])

        # Get label values
        if isinstance(field, LikertField) and getattr(field, "left_label"):
            left_label = field.left_label
        else:
            left_label = self.left_label
        if isinstance(field, LikertField) and getattr(field, "right_label"):
            right_label = field.right_label
        else:
            right_label = self.right_label

        # Set them in context
        kwargs.setdefault("extra_context", {})["left_label"] = left_label
        kwargs.setdefault("extra_context", {})["right_label"] = right_label
        return super().render(*args, **kwargs)


class MAIDAPreSurveyForm(forms.Form):
    """
    A form for the MAIDA pre-survey.
    This form is used to collect data for the MAIDA pre-survey.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.template_pack = "maida-forms"
        self.helper.layout = Layout(
            Div(
                HTML("<h4 class='maida-form-section-header'>General Information</h4>"),
                'sex',
                'age',
                'education',
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Health Literacy and Medical Background</h4>"),
                CrispyLikertField(
                    'familiarity_with_medical_imaging',
                ),
                'previously_discussed_radiology',
                'previously_tried_to_understand',
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Technology Comfort</h4>"),
                CrispyLikertField(
                    'comfort_watching_educational_videos',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Baseline Comprehension</h4>"),
                'know_part_of_body_in_report',
                CrispyLikertField(
                    'understanding_of_the_report',
                ),
                CrispyLikertField(
                    'understanding_of_the_image',
                ),
                CrispyLikertField(
                    'significance_of_findings',
                ),
                CrispyLikertField(
                    'can_explain_findings_to_family_members',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Confidence & Emotional State</h4>"),
                CrispyLikertField(
                    'confidence_discussing_with_provider',
                ),
                CrispyLikertField(
                    'worried_about_misunderstanding_findings',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Trust in Technology/AI</h4>"),
                CrispyLikertField(
                    'trust_ai_tools',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Open-ended questions</h4>"),
                'confusing_aspects_of_findings',
                'concerns_about_using_ai',
            ),
        )

    sex = forms.ChoiceField(
        label="Sex",
        help_text="Please select your sex",
        choices=(
            ("female", _("Female")),
            ("male", _("Male")),
            ("other", _("Other")),
        )
    )
    age = forms.IntegerField(
        label="Age",
        min_value=0,
        max_value=120,
        help_text=_("Please enter your age"),
    )
    education = forms.ChoiceField(
        label=_("Education Level"),
        help_text=_("Please select your highest level of education"),
        choices=(
            ("primary_school", _("Primary school")),
            ("middle_school", _("Middle school")),
            ("high_school", _("High school")),
            ("college_or_above", _("College or above")),
        )
    )
    familiarity_with_medical_imaging = LikertField(
        label=_("How familiar are you with medical imaging (X-ray, CT, MRI)?"),
        left_label=_("Not familiar at all"),
        right_label=_("Very familiar"),
    )
    previously_discussed_radiology = forms.ChoiceField(
        label=_("Have you previously discussed radiology findings with a medical professional?"),
        widget=forms.RadioSelect,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
        ],
    )
    previously_tried_to_understand = forms.ChoiceField(
        label=_("Have you previously tried to understand your reports by yourself (e.g., through online searching)?"),
        widget=forms.RadioSelect,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
        ],
    )
    comfort_watching_educational_videos = LikertField(
        label=_("How comfortable are you with watching educational videos on a computer or smartphone?"),
        left_label=_("Not comfortable at all"),
        right_label=_("Very comfortable"),
    )
    know_part_of_body_in_report = forms.ChoiceField(
        label=_("Do you know which part of your body was described in the report?"),
        widget=forms.RadioSelect,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
        ],
    )
    understanding_of_the_report = LikertField(
        label=_("How would you rank your understanding of the radiology report?"),
        left_label=_("Not at all"),
        right_label=_("Very well"),
    )
    understanding_of_the_image = LikertField(
        label=_("How would you rank your understanding of the radiology image?"),
        left_label=_("Not at all"),
        right_label=_("Very well"),
    )
    significance_of_findings = LikertField(
        label=_("Do you know the significance of the finding(s)?"),
        left_label=_("Not at all"),
        right_label=_("Very well"),
    )
    can_explain_findings_to_family_members = LikertField(
        label=_("I can explain the main findings of my radiology report to my family members."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    confidence_discussing_with_provider = LikertField(
        label=_("I feel confident discussing my radiology results with my healthcare provider."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    worried_about_misunderstanding_findings = LikertField(
        label=_("I am worried about misunderstanding my radiology findings."),
        left_label=_("Not worried"),
        right_label=_("Very worried"),
    )
    trust_ai_tools = LikertField(
        label=_("I generally trust AI tools to provide accurate explanations for my radiology findings."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    confusing_aspects_of_findings = SanitizedCharField(
        label=_("What aspects of your radiology report do you find most confusing or unclear?"),
        widget=forms.Textarea,
        required=False,
    )
    concerns_about_using_ai = SanitizedCharField(
        label=_("Do you have any concerns about using AI or videos to explain medical findings?"),
        widget=forms.Textarea,
        required=False,
    )


class MAIDAPostSurveyForm(forms.Form):
    """
    A form for the MAIDA post-survey.
    This form is used to collect data for the MAIDA post-survey.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.template_pack = "maida-forms"
        self.helper.layout = Layout(
            Div(
                HTML("<h4 class='maida-form-section-header'>Video Questions</h4>"),
                'what_found_helpful_about_video_report',
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Comprehension</h4>"),
                'know_part_of_body_in_report',
                CrispyLikertField(
                    'understanding_of_the_report',
                ),
                CrispyLikertField(
                    'understanding_of_the_image',
                ),
                CrispyLikertField(
                    'significance_of_findings',
                ),
                CrispyLikertField(
                    'can_explain_findings_to_family_members',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Confidence & Emotional State</h4>"),
                CrispyLikertField(
                    'confidence_discussing_with_provider',
                ),
                CrispyLikertField(
                    'worried_about_misunderstanding_findings',
                ),
                CrispyLikertField(
                    'feel_less_anxious',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Technology Acceptance & Trust</h4>"),
                CrispyLikertField(
                    'using_ai_improves_understanding',
                ),
                CrispyLikertField(
                    'ai_video_is_easy_to_follow',
                ),
                CrispyLikertField(
                    'trust_ais_explanation',
                ),
                CrispyLikertField(
                    'would_like_future_ai_explanations',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>User Experience & Satisfaction</h4>"),
                CrispyLikertField(
                    'experience_with_video',
                ),
                CrispyLikertField(
                    'would_recommend_video_explanation',
                ),
            ),
            Div(
                HTML("<h4 class='maida-form-section-header'>Open-ended questions</h4>"),
                'still_confusing_aspects_of_findings',
                'comments_or_feedback',
            ),
        )

    what_found_helpful_about_video_report = forms.MultipleChoiceField(
        label=_("What did you find helpful about the video report?"),
        help_text=_("Check all that apply"),
        widget=forms.CheckboxSelectMultiple,
        choices=[
            ("findings_highlighted", _("The findings highlighted in the images")),
            ("avatar_language", _("The avatar using language that was easy to understand")),
            ("comprisons_to_normal_studies", _("Seeing comparisons to normal studies (if applicable)")),
            ("comparisons_to_older_studies", _("Seeing comparisons to your older studies (if applicable)")),
            ("3d_images", _("Use of 3D images")),
            ("easier_than_written", _("Easier to understand than the written report")),
            ("side_by_side_comparison_to_normal_images", _("Side-by-side comparison with normal images")),
        ],
    )
    know_part_of_body_in_report = forms.ChoiceField(
        label=_("Do you know which part of your body was described in the report?"),
        widget=forms.RadioSelect,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
        ],
    )
    understanding_of_the_report = LikertField(
        label=_("How would you rank your understanding of the radiology report?"),
        left_label=_("Not at all"),
        right_label=_("Very well"),
    )
    understanding_of_the_image = LikertField(
        label=_("How would you rank your understanding of the radiology image?"),
        left_label=_("Not at all"),
        right_label=_("Very well"),
    )
    significance_of_findings = LikertField(
        label=_("Do you know the significance of the finding(s)?"),
        left_label=_("Not at all"),
        right_label=_("Very well"),
    )
    can_explain_findings_to_family_members = LikertField(
        label=_("I can explain the main findings of my radiology report to my family members."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    confidence_discussing_with_provider = LikertField(
        label=_("I feel confident discussing my radiology results with my healthcare provider."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    worried_about_misunderstanding_findings = LikertField(
        label=_("I am worried about misunderstanding my radiology findings."),
        left_label=_("Not worried"),
        right_label=_("Very worried"),
    )
    feel_less_anxious = LikertField(
        label=_("I feel less anxious about my condition after viewing the video."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    using_ai_improves_understanding = LikertField(
        label=_("Using the AI video explanation improves my understanding of my radiology findings."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    ai_video_is_easy_to_follow = LikertField(
        label=_("The AI video explanation is easy to follow and interact with."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    trust_ais_explanation = LikertField(
        label=_("I trust the AI’s explanation to accurately explain my radiology findings."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    would_like_future_ai_explanations = LikertField(
        label=_("I would like to receive this type of AI-based explanation for future radiology reports."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    experience_with_video = LikertField(
        label=_("Overall, how was your experience with the video report?"),
        left_label=_("Poor"),
        right_label=_("Excellent"),
    )
    would_recommend_video_explanation = LikertField(
        label=_("I would recommend this type of video explanation to other people to understand their radiology findings."),
        left_label=_("Strongly disagree"),
        right_label=_("Strongly agree"),
    )
    still_confusing_aspects_of_findings = SanitizedCharField(
        label=_("What aspects of your radiology report do you still find confusing or unclear?"),
        widget=forms.Textarea,
        required=False,
    )
    comments_or_feedback = SanitizedCharField(
        label=_("Please enter any additional comments or feedback about the video report."),
        widget=forms.Textarea,
        required=False,
    )
