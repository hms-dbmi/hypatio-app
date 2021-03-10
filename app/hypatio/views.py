from django.shortcuts import render

from hypatio.dbmiauthn_services import DBMIAuthn

@DBMIAuthn.public_user_auth_and_jwt
def index(request, template_name='index.html'):
    """
    Homepage for the DBMI Portal
    """

    context = {}

    return render(request, template_name, context=context)
