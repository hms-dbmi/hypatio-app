import json
import logging
import sys
import requests

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from pyauth0jwt.auth0authenticate import user_auth_and_jwt, public_user_auth_and_jwt

from .forms import ContactForm
from .models import DataProject
from hypatio.scireg_services import request_project_access

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

    r = request_project_access(request.COOKIES.get("DBMI_JWT", None), request.POST['project_key'])

    return render(request, template_name, {"dua_results": r.json()["results"][0],
                                           "project_key": request.POST['project_key']})

@user_auth_and_jwt
def submit_request(request, template_name='dataprojects/submit_request.html'):

    user_jwt = request.COOKIES.get("DBMI_JWT", None)
    jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

    data_request = {"project": request.POST['project_key'], "user": request.user.email}

    data_dua_sign = {"data_use_agreement": request.POST['data_use_agreement'],
                     "user": request.user.email,
                     "agreement_text": request.POST['agreement_text']}

    create_auth_request_url = settings.CREATE_REQUEST_URL
    create_dua_sign_request_url = settings.CREATE_DUA_SIGN

    requests.post(create_auth_request_url, headers=jwt_headers, data=json.dumps(data_request))
    requests.post(create_dua_sign_request_url, headers=jwt_headers, data=json.dumps(data_dua_sign))

    return render(request, template_name)


@public_user_auth_and_jwt
def listDataprojects(request, template_name='dataprojects/list.html'):
    user = None

    permission_dictionary = {}
    project_permission_setup = {}
    access_request_dictionary = {}

    all_data_projects = DataProject.objects.all()

    # Okay, definitely not a real user.
    if not request.user.is_authenticated():
        user_logged_in = False
    else:
        user_logged_in = True
        user = request.user

        user_jwt = request.COOKIES.get("DBMI_JWT", None)

        if user_jwt:

            jwt_headers = {"Authorization": "JWT " + user_jwt, 'Content-Type': 'application/json'}

            permissions_url = settings.PERMISSION_SERVER
            project_permissions_setup = settings.PROJECT_PERMISSION_URL
            access_requests_url = settings.GET_ACCESS_REQUESTS

            # ------------------
            # Get Project Permissions & Requirements
            r = requests.get(project_permissions_setup, headers=jwt_headers)

            try:
                for project_setup in r.json()["results"]:
                    for project in all_data_projects:
                        if project.project_key == project_setup["project_key"]:
                            project_permission_setup[project.project_key] = project_setup
            except:
                project_permission_setup = {}

            # ------------------

            # ------------------
            # Get user permissions.
            r = requests.get(permissions_url, headers=jwt_headers)

            try:
                for project_permission in r.json()["results"]:
                    for project in all_data_projects:
                        if project.project_key == project_permission["project"]:
                            permission_dictionary[project.project_key] = project_permission["permission"]
            except:
                permission_dictionary = {}
            # ------------------


            # ------------------
            # Find what requests for access the user has already made.
            r = requests.get(access_requests_url, headers=jwt_headers)

            try:
                for access_request in r.json()["results"]:
                    for project in all_data_projects:
                        if project.project_key == access_request["project"]:
                            access_request_dictionary[project.project_key] = {
                                "date_requested": access_request["date_requested"],
                                "request_granted": access_request["request_granted"],
                                "date_request_granted": access_request["request_granted"],
                            }
            except:
                access_request_dictionary = {}
            # ------------------

    logger.debug("Project Permission Setup %s" % project_permission_setup)
    logger.debug("permission_dictionary %s" % permission_dictionary)
    logger.debug("all_data_projects %s" % all_data_projects)

    return render(request, template_name, {"dataprojects": all_data_projects,
                                           "user_logged_in": user_logged_in,
                                           "user": user,
                                           "ssl_setting": settings.SSL_SETTING,
                                           "account_server_url": settings.ACCOUNT_SERVER_URL,
                                           "profile_server_url": settings.SCIREG_SERVER_URL,
                                           "permission_dictionary": permission_dictionary,
                                           "project_permission_setup": project_permission_setup,
                                           "access_request_dictionary": access_request_dictionary})

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
