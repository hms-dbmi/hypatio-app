import logging

from django.conf import settings
from django.shortcuts import render
from pyauth0jwt.auth0authenticate import public_user_auth_and_jwt

from .forms import ContactForm

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

# Get an instance of a logger
logger = logging.getLogger(__name__)

@public_user_auth_and_jwt
def contact_form(request):

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        logger.debug("[P2M2][DEBUG][contact_form] Processing contact form  - " + str(request.user.id))

        # Process the form.
        form = ContactForm(request.POST)
        if form.is_valid():
            logger.debug("[P2M2][DEBUG][contact_form] Form is valid - " + str(request.user.id))

            # Form the context.
            context = {
                'from_email': form.cleaned_data['email'],
                'from_name': form.cleaned_data['name'],
                'message': form.cleaned_data['message'],
            }

            # List out the recipients.
            recipients = settings.CONTACT_FORM_RECIPIENTS.split(',')

            # Send it out.
            success = email_send(subject='PPM Contact Form Inquiry',
                                 recipients=recipients,
                                 message='email_contact',
                                 extra=context)

            # Check how the request was made.
            if request.is_ajax():
                return HttpResponse('SUCCESS', status=200) if success else HttpResponse('ERROR', status=500)
            else:
                if success:
                    # Set a message.
                    messages.success(request, 'Thanks, your message has been submitted!')
                else:
                    messages.error(request, 'An unexpected error occurred, please try again')
                return HttpResponseRedirect(reverse('dashboard:dashboard'))
        else:
            logger.error("[P2M2][ERROR][contact_form] Form is invalid! - " + str(request.user.id))

            # Check how the request was made.
            if request.is_ajax():
                return HttpResponse('INVALID', status=500)
            else:
                messages.error(request, 'An unexpected error occurred, please try again')
                return HttpResponseRedirect(reverse('dashboard:dashboard'))

    # if a GET (or any other method) we'll create a blank form
    else:
        if not request.user.is_anonymous:
            logger.debug("[P2M2][DEBUG][contact_form] Generating contact form  - " + str(request.user.id))

            # Set initial values.
            initial = {
                'email': request.user.email
            }
        else:
            # Set initial values.
            initial = {
                'email': "Please enter your e-mail here."
            }

        # Generate and render the form.
        form = ContactForm(initial=initial)
        return render(request, 'contact/contact.html', {'contact_form': form})

def email_send(subject=None, recipients=None, message=None, extra=None):
    """
    Send an e-mail to a list of participants with the given subject and message.
    Extra is dictionary of variables to be swapped into the template.
    """
    for r in recipients:
        sent_without_error = True

        extra["user_email"] = r

        msg_html = render_to_string('email/%s.html' % message, extra)
        msg_plain = render_to_string('email/%s.txt' % message, extra)

        logger.debug("[P2M2][DEBUG][email_send] About to send e-mail.")

        try:
            msg = EmailMultiAlternatives(subject, msg_plain, settings.DEFAULT_FROM_EMAIL, [r])
            msg.attach_alternative(msg_html, "text/html")
            msg.send()
        except gaierror:
            logger.error("[P2M2][DEBUG][email_send] Could not send mail! Possible bad server connection.")
            sent_without_error = False
        except Exception as ex:
            print(ex)
            sent_without_error = False

        logger.debug("[P2M2][DEBUG][email_send] E-Mail Status - " + str(sent_without_error))

    return sent_without_error
