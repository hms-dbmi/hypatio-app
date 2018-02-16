import json
import logging
import requests



from django.contrib import messages
from django.conf import settings
from django.shortcuts import render
from pyauth0jwt.auth0authenticate import user_auth_and_jwt, validate_jwt, logout_redirect
from .forms import RegistrationForm
from django.http import HttpResponse

from hypatio.sciauthz_services import SciAuthZ

from hypatio import scireg_services


# Get an instance of a logger
logger = logging.getLogger(__name__)

@user_auth_and_jwt
def update_profile(request):

    user = request.user
    user_logged_in = True
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    # If the JWT has expired or the user doesn't have one, force the user to login again
    if user_jwt is None or validate_jwt(request) is None:
        logout_redirect(request)

    # The JWT token that will get passed in API calls
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    # If there was a POST request, a form was submitted
    if request.method == 'POST':

        # Process the form
        registration_form = RegistrationForm(request.POST)
        if registration_form.is_valid():
            logger.debug('[HYPATIO][DEBUG] Profile form fields submitted: ' + json.dumps(registration_form.cleaned_data))

            # Create a new registration with a POST
            if registration_form.cleaned_data['id'] == "":
                requests.post(settings.SCIREG_REGISTRATION_URL, headers=jwt_headers, data=json.dumps(registration_form.cleaned_data), verify=False)
            # Update an existing registration with a PUT to the specific ID
            else:
                registration_url = settings.SCIREG_REGISTRATION_URL + registration_form.cleaned_data['id'] + '/'
                requests.put(registration_url, headers=jwt_headers, data=json.dumps(registration_form.cleaned_data), verify=False)

            return HttpResponse(200)
        else:
            # logger.debug('[HYPATIO][DEBUG] Profile form errors: ' + form.errors.as_json())
            # TODO Not implemented
            return HttpResponse(status=500)

@user_auth_and_jwt
def profile(request, template_name='profile/profile.html'):

    user = request.user
    user_logged_in = True
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(request, 'n2c2-t1')

    # The JWT token that will get passed in API calls
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    # Query SciReg to get the user's information
    registration_info = requests.get(settings.SCIREG_REGISTRATION_URL, headers=jwt_headers, verify=False).json()

    logger.debug('[HYPATIO][DEBUG] Registration info ' + json.dumps(registration_info))

    if registration_info['count'] != 0:
        registration_info = registration_info["results"][0]
        registration_form = RegistrationForm(initial=registration_info)

        new_user = False
    else:
        # User does not have a registration in scireg, present them with a blank form to complete and prepopulate the email
        registration_form = RegistrationForm(initial={'email': user.email}, new_registration=True)
        new_user = True

    # Check for a returning task and set messages accordingly
    get_task_context_data(request)

    # Generate and render the form.
    return render(request, template_name, {'registration_form': registration_form,
                                            'user': user,
                                            'is_manager': is_manager,
                                            'new_user': new_user,
                                            'user_logged_in': user_logged_in})

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

    logger.debug("[P2M2][DEBUG][recaptcha_check] Sending Captcha results to google - " + str(request.user.id))

    verify_rs = requests.get(url, params=params, verify=True)
    verify_rs = verify_rs.json()
    response["status"] = verify_rs.get("success", False)
    response['message'] = verify_rs.get('error-codes', None) or "Unspecified error."

    return response

@user_auth_and_jwt
def send_confirmation_email_view(request):
    logger.debug("[P2M2][DEBUG][send_confirmation_email_view] Sending user verification e-mail - " + str(request.user.id))

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
