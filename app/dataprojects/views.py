import json
import logging
import sys
import requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from pyauth0jwt.auth0authenticate import user_auth_and_jwt, public_user_auth_and_jwt, validate_jwt, logout_redirect

from .forms import ContactForm
from .models import DataProject, DataUseAgreement, DataUseAgreementSign

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from socket import gaierror

# Get an instance of a logger
logger = logging.getLogger(__name__)

@user_auth_and_jwt
def signout(request):
    logout(request)
    response = redirect(settings.AUTH0_LOGOUT_URL)
    response.delete_cookie('DBMI_JWT', domain=settings.COOKIE_DOMAIN)
    return response

@user_auth_and_jwt
def request_access(request, template_name='dataprojects/access_request.html'):

    project = DataProject.objects.get(project_key=request.POST['project_key'])

    # There may be multiple DUAs for a project for the user to choose from
    data_use_agreements = DataUseAgreement.objects.filter(project=project).values()

    return render(request, template_name, {"project_key": request.POST['project_key'],
                                           "data_use_agreements": data_use_agreements})

@user_auth_and_jwt
def submit_request(request):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    dua = DataUseAgreement.objects.get(id=request.POST['dua_id'])

    date_requested = datetime.now().isoformat()

    # Save the signed DUA
    dua_signed = DataUseAgreementSign(data_use_agreement=dua,
                                      user=request.user,
                                      date_signed=date_requested,
                                      agreement_text=request.POST['agreement_text'])
    dua_signed.save()

    data_request = {"user": request.user.email,
                    "item": request.POST['project_key']}

    # Send the authorization request to SciAuthZ
    create_auth_request_url = settings.CREATE_REQUEST_URL
    requests.post(create_auth_request_url, headers=jwt_headers, data=json.dumps(data_request), verify=False)

    return HttpResponse(200)

@public_user_auth_and_jwt
def list_data_projects(request, template_name='dataprojects/list.html'):

    all_data_projects = DataProject.objects.all()

    data_projects = []
    projects_with_view_permissions = []
    projects_with_access_requests = {}

    if not request.user.is_authenticated():
        user = None
        user_logged_in = False
    else:
        user = request.user
        user_logged_in = True
        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        # If the JWT has expired or the user doesn't have one, force the user to login again
        if user_jwt is None or validate_jwt(request) is None:
            logout_redirect(request)

        # The JWT token that will get passed in API calls
        jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

        # Get all of the user's VIEW permissions
        permissions_url = settings.PERMISSION_SERVER
        user_permissions = requests.get(permissions_url, headers=jwt_headers, verify=False).json()["results"]

        for user_permission in user_permissions:
            if user_permission['permission'] == 'VIEW':
                projects_with_view_permissions.append(user_permission['item'])

        # Get all of the user's permission requests
        access_requests_url = settings.GET_ACCESS_REQUESTS
        user_access_requests = requests.get(access_requests_url, headers=jwt_headers, verify=False).json()["results"]

        for access_request in user_access_requests:
            projects_with_access_requests[access_request['item']] = {
                'date_requested': access_request['date_request_granted'],
                'request_granted': access_request['request_granted'],
                'date_request_granted': access_request['date_request_granted']}

    # Build the dictionary with all project and permission information needed
    for project in all_data_projects:

        user_has_view_permissions = project.project_key in projects_with_view_permissions

        if project.project_key in projects_with_access_requests:
            user_requested_access_on = projects_with_access_requests[project.project_key]['date_requested']
            user_requested_access = True
        else:
            user_requested_access_on = None
            user_requested_access = False

        # Package all the necessary information into one dictionary
        project = {"name": project.name,
                   "short_description": project.short_description,
                   "description": project.description,
                   "project_key": project.project_key,
                   "project_url": project.project_url,
                   "permission_scheme": project.permission_scheme,
                   "user_has_view_permissions": user_has_view_permissions,
                   "user_requested_access": user_requested_access,
                   "user_requested_access_on": user_requested_access_on}

        data_projects.append(project)

    return render(request, template_name, {"data_projects": data_projects,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL})

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
        return render(request, 'dataprojects/contact.html', {'contact_form': form})

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
