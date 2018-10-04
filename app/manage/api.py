import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from pyauth0jwt.auth0authenticate import user_auth_and_jwt

from hypatio.sciauthz_services import SciAuthZ

from manage.forms import EditHostedFileForm

from projects.models import DataProject
from projects.models import HostedFile
from projects.templatetags import projects_extras

# Get an instance of a logger
logger = logging.getLogger(__name__)

@user_auth_and_jwt
def set_dataproject_registration_status(request):
    """
    An HTTP POST endpoint for opening or closing registration to a DataProject.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.POST.get("project_key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_dataproject_registration_status] User {email} does not have MANAGE permissions for item {project_key}.',
            email=user.email,
            project_key=project_key
        )
        return HttpResponse("Error: permissions.", status=403)

    registration_status = request.POST.get("registration_status")

    if registration_status == "open":
        project.registration_open = True
    elif registration_status == "close":
        project.registration_open = False
    else:
        return HttpResponse("Error: invalid status.", status=400)

    project.save()

    response_html = render_to_string(
        'manage/registration-status.html',
        context={
            'project': project,
        }
    )

    return HttpResponse(response_html)

@user_auth_and_jwt
def set_dataproject_visible_status(request):
    """
    An HTTP POST endpoint for making a DataProject publicly visible or not.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.POST.get("project_key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_dataproject_visible_status] User {email} does not have MANAGE permissions for item {project_key}.',
            email=user.email,
            project_key=project_key
        )
        return HttpResponse("Error: permissions.", status=403)

    visibile_status = request.POST.get("visible_status")

    if visibile_status == "visible":
        project.visible = True
    elif visibile_status == "invisible":
        project.visible = False
    else:
        return HttpResponse("Error: Invalid status.", status=400)

    project.save()

    response_html = render_to_string(
        'manage/visible-status.html',
        context={
            'project': project,
        }
    )

    return HttpResponse(response_html)

@user_auth_and_jwt
def set_dataproject_details(request):
    """
    An HTTP POST endpoint for setting some details about a DataProject.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.POST.get("project_key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][set_dataproject_visible_status] User {email} does not have MANAGE permissions for item {project_key}.',
            email=user.email,
            project_key=project_key
        )
        return HttpResponse("Error: permissions.", status=403)

    name = request.POST.get("name", "")
    short_description = request.POST.get("short-description", "")
    description = request.POST.get("description", "")

    if name == "":
        return HttpResponse("Error: project name required.", status=400)
    if short_description == "":
        return HttpResponse("Error: project short description required.", status=400)
    if description == "":
        return HttpResponse("Error: project description required.", status=400)

    project.name = name
    project.short_description = short_description
    project.description = description

    try:
        project.save()
    except Exception as ex:
        return HttpResponse("Error: project details failed to save.", status=400)

    response_html = render_to_string(
        'manage/project-details.html',
        context={
            'project': project,
            'message': "Changes saved!"
        }
    )

    return HttpResponse(response_html)

@user_auth_and_jwt
def get_static_agreement_form_html(request):
    """
    An HTTP GET endpoint for Intercooler.js requests to get the HTML contents of an
    agreement form file and return them as HTML.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.GET.get("project-key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][get_static_agreement_form_html] User {email} does not have MANAGE permissions for item {project_key}.',
            email=user.email,
            project_key=project_key
        )
        return HttpResponse("Error: permissions.", status=403)

    agreement_form_id = request.GET.get('form-id', "")

    try:
        agreement_form = project.agreement_forms.get(id=agreement_form_id)
    except ObjectDoesNotExist:
        return HttpResponse("Error: form not found.", status=404)

    if agreement_form.form_file_path is None or agreement_form.form_file_path == "":
        return HttpResponse("Error: form file path is missing.", status=400)

    form_contents = projects_extras.get_html_form_file_contents(agreement_form.form_file_path)
    return HttpResponse(form_contents)

@user_auth_and_jwt
def get_hosted_file_edit_form(request):
    """
    An HTTP GET endpoint for requests to get an HTML form for editing an
    existing HostedFile.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    project_key = request.GET.get("project-key")
    project = get_object_or_404(DataProject, project_key=project_key)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][get_static_agreement_form_html] User {email} does not have MANAGE permissions for item {project_key}.',
            email=user.email,
            project_key=project_key
        )
        return HttpResponse("Error: permissions.", status=403)

    hosted_file_uuid = request.GET.get("hosted-file-uuid")

    try:
        hosted_file = HostedFile.objects.get(project=project, uuid=hosted_file_uuid)
    except ObjectDoesNotExist:
        return HttpResponse("Error: file not found.", status=404)

    edit_hosted_file_form = EditHostedFileForm(instance=hosted_file)

    response_html = render_to_string(
        'manage/edit-hosted-file-form.html',
        context={
            'form': edit_hosted_file_form,
            'file': hosted_file
        },
        request=request
    )
    return HttpResponse(response_html)

@user_auth_and_jwt
def process_hosted_file_edit_form_submission(request):
    """
    An HTTP POST endpoint for processing a submitted form for editing a hosted file.
    """

    user = request.user
    user_jwt = request.COOKIES.get("DBMI_JWT", None)

    file_uuid = request.POST.get("file-uuid")
    project_id = request.POST.get("project")
    project = get_object_or_404(DataProject, id=project_id)

    sciauthz = SciAuthZ(settings.AUTHZ_BASE, user_jwt, user.email)
    is_manager = sciauthz.user_has_manage_permission(project.project_key)

    if not is_manager:
        logger.debug(
            '[HYPATIO][DEBUG][get_static_agreement_form_html] User {email} does not have MANAGE permissions for item {project_key}.',
            email=user.email,
            project_key=project.project_key
        )
        return HttpResponse("Error: permissions.", status=403)

    hosted_file = HostedFile.objects.get(project=project, uuid=file_uuid)
    edit_hosted_file_form = EditHostedFileForm(request.POST, instance=hosted_file)

    # TODO show error messages
    if not edit_hosted_file_form.is_valid():
        return HttpResponse(edit_hosted_file_form.errors.as_json(), status=400)

    try:
        edit_hosted_file_form.save()
    except Exception:
        # TODO do something on failure
        return HttpResponse("Error: failed to save object", status=500)

    return HttpResponse("File updated.", status=200)
