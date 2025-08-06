import json
import logging
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from dbmi_client.authn import logout_redirect_url
from dbmi_client import reg

from hypatio import scireg_services
from hypatio.auth0authenticate import user_auth_and_jwt
from profile.forms import RegistrationForm

# Get an instance of a logger
logger = logging.getLogger(__name__)


@user_auth_and_jwt
def signout(request):
    logout(request)
    response = redirect(logout_redirect_url(request, request.build_absolute_uri(reverse("index"))))
    return response


@user_auth_and_jwt
def update_profile(request):

    # If there was a POST request, a form was submitted
    if request.method == 'POST':

        # Process the form
        registration_form = RegistrationForm(request.POST, initial={"email": request.user.email})
        if registration_form.is_valid():

            # Update it
            reg.update_dbmi_user(request, **registration_form.cleaned_data)

            response = HttpResponse(200)

            # Setup the script run.
            response["HX-Trigger"] = json.dumps({"showNotification": {
                "level" : "success",
                "icon": "thumbs-up",
                "message" : "Institutional members updated",
            }})

            return response

        else:
            logger.debug(f'Update profile errors: {registration_form.errors.as_json()}')
            return HttpResponse(registration_form.errors.as_json(), status=400)

    else:
        return HttpResponse(405)

@user_auth_and_jwt
def profile(request, template_name='profile/profile.html'):

    # Set defaults
    initial = {
        "email": request.user.email,
    }
    email_confirmed = False
    new_registration = True

    # Get a profile if it exists
    reg_profile = reg.get_dbmi_user(request, request.user.email)
    if reg_profile:

        # Get whether they've confirmed their email or not
        email_confirmed = reg_profile.get("email_confirmed", False)

        # Use their existing profile
        initial = reg_profile
        new_registration = False

    # Check for a returning task and set messages accordingly
    get_task_context_data(request)

    context = {
        'registration_form': RegistrationForm(
            initial=initial,
            new_registration=new_registration,
            email_confirmed=email_confirmed,
        ),
    }

    # Generate and render the form.
    return render(request, template_name, context=context)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def recaptcha_check(request):
    """
    Send a query over to google's servers with the result of the Captcha to see whether it's valid.
    :param request:
    :return:
    """
    response = {}

    captcha_rs = request.POST.get('g-recaptcha-response')

    url = "https://www.google.com/recaptcha/api/siteverify"

    params = {
        'secret': settings.RECAPTCHA_KEY,
        'response': captcha_rs,
        'remoteip': get_client_ip(request)
    }

    logger.debug("[HYPATIO][DEBUG][recaptcha_check] Sending Captcha results to google - " + str(request.user.id))

    verify_rs = requests.get(url, params=params, verify=True)
    verify_rs = verify_rs.json()
    response["status"] = verify_rs.get("success", False)
    response['message'] = verify_rs.get('error-codes', None) or "Unspecified error."

    return response

@user_auth_and_jwt
def send_confirmation_email_view(request):
    logger.debug("[HYPATIO][DEBUG][send_confirmation_email_view] Sending user verification e-mail - " + str(request.user.id))

    if request.method == 'POST':

        # Need to verify the Google Recaptcha before sending e-mail.
        recaptcha_response = recaptcha_check(request)

        if recaptcha_response["status"]:
            scireg_services.send_confirmation_email(request.COOKIES.get("DBMI_JWT", None), request.POST.get('current_uri'))
            return HttpResponse("SENT")
        else:
            return HttpResponse("FAILED_RECAPTCHA")
    else:
        return HttpResponse("INVALID_POST")


def get_task_context_data(request):
    logger.debug("[profile][get_task_context_data] Checking for tasks - " + str(request.user.id))

    # Check for a returning task
    task = request.GET.get('task')
    state = request.GET.get('state')
    message = request.GET.get('message')

    # Handle email confirm
    if task and state and message and task == 'email_confirm':
        logger.debug("[profile][get_task_context_data] Handling task '{}' - '{}' for {}".format(
            task, state, request.user.id))

        # Stash a message for the user.
        if state == 'success':
            messages.success(request, message, extra_tags='success', fail_silently=True)

        elif state == 'failed':
            messages.error(request, message, extra_tags='danger', fail_silently=True)
