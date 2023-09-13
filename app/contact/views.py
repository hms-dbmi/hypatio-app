import logging

from hypatio.auth0authenticate import public_user_auth_and_jwt

from contact.forms import ContactForm

from projects.models import DataProject
from manage.views import is_ajax

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render
from django.template.loader import render_to_string

# Get an instance of a logger
logger = logging.getLogger(__name__)

@public_user_auth_and_jwt
def contact_form(request, project_key=None):

    # If this is a POST request we need to process the form data.
    if request.method == 'POST':
        logger.debug("[HYPATIO][DEBUG][contact_form] Processing contact form  - " + str(request.user.id))

        # Process the form.
        form = ContactForm(request.POST)
        if form.is_valid():
            logger.debug("[HYPATIO][DEBUG][contact_form] Form is valid - " + str(request.user.id))

            # Form the context.
            context = {
                'from_email': form.cleaned_data['email'],
                'from_name': form.cleaned_data['name'],
                'message': form.cleaned_data['message'],
                'project': form.cleaned_data['project']
            }

            # If the message is related to a project, set the recipient to the project supervisor
            try:
                project = DataProject.objects.get(project_key=form.cleaned_data['project'])

                if project.project_supervisors != '' and project.project_supervisors is not None:
                    recipients = project.project_supervisors.split(',')
                else:
                    recipients = settings.CONTACT_FORM_RECIPIENTS

            except ObjectDoesNotExist:
                recipients = settings.CONTACT_FORM_RECIPIENTS

            # Send it out.
            success = email_send(subject='DBMI Portal - Contact Inquiry Received',
                                 recipients=recipients,
                                 email_template='email_contact',
                                 extra=context)

            # Check how the request was made.
            if is_ajax(request):
                return HttpResponse('SUCCESS', status=200) if success else HttpResponse('ERROR', status=500)
            else:
                if success:
                    # Set a message.
                    messages.success(request, 'Thanks, your message has been submitted!')
                else:
                    messages.error(request, 'An unexpected error occurred, please try again')
                return HttpResponseRedirect(reverse(
                    'projects:view-project',
                    kwargs={'project_key': form.cleaned_data['project']}
                ))
        else:
            logger.error("[HYPATIO][ERROR][contact_form] Form is invalid! - " + str(request.user.id))

            # Check how the request was made.
            if is_ajax(request):
                return HttpResponse('INVALID', status=500)
            else:
                messages.error(request, 'An unexpected error occurred, please try again')
                return HttpResponseRedirect(reverse(
                    'projects:view-project',
                    kwargs={'project_key': form.cleaned_data['project']}
                ))

    # If a GET (or any other method) we'll create a blank form.
    initial = {}

    if not request.user.is_anonymous:
        initial['email'] = request.user.email

    # If a project key was supplied and it matches a real project, pre-populate the form with it.
    if project_key is not None:
        try:
            data_project = DataProject.objects.get(project_key=project_key)
            initial['project'] = data_project
        except ObjectDoesNotExist:
            pass

    # Generate and render the form.
    form = ContactForm(initial=initial)
    return render(request, 'contact/contact.html', {'contact_form': form})

def email_send(subject=None, recipients=None, email_template=None, extra=None):
    """
    Send an e-mail to a list of recipients with the given subject and email_template.
    Extra is dictionary of variables to be swapped into the template.
    """
    sent_without_error = True

    msg_html = render_to_string('email/%s.html' % email_template, extra)
    msg_plain = render_to_string('email/%s.txt' % email_template, extra)

    logger.debug("[HYPATIO][DEBUG][email_send] About to send e-mail.")

    try:
        msg = EmailMultiAlternatives(subject=subject,
                                     body=msg_plain,
                                     from_email=settings.EMAIL_FROM_ADDRESS,
                                     reply_to=(settings.EMAIL_REPLY_TO_ADDRESS, ),
                                     to=recipients)
        msg.attach_alternative(msg_html, "text/html")
        msg.send()
    except Exception as ex:
        logger.exception(ex, exc_info=True, extra={
            'email': email_template, 'extra': extra
        })
        sent_without_error = False

    logger.debug("[HYPATIO][DEBUG][email_send] E-Mail Status - " + str(sent_without_error))

    return sent_without_error
