from stronghold.decorators import public
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
import json
from django.contrib import auth as django_auth
from django.contrib.auth import login
import jwt
import base64

import requests

@public
def sso_login(request):
    if request.user.is_authenticated():
        redirect_url = request.GET.get("next", settings.AUTH0_SUCCESS_URL)
        return redirect(redirect_url)

    jwt_string = request.COOKIES.get("DBMI_JWT",None)

    try:
        payload = jwt.decode(jwt_string, base64.b64decode(settings.AUTH0_SECRET, '-_'), algorithms=['HS256'], audience=settings.AUTH0_CLIENT_ID)
    except jwt.InvalidTokenError:
        return HttpResponse("Possible bad token.")

    request.session['profile'] = payload
    user = django_auth.authenticate(**payload)

    if user:
        redirect_url = request.GET.get("next", settings.AUTH0_SUCCESS_URL)
        login(request, user)
        return redirect(redirect_url)

    return HttpResponse("SSO LOGIN PAGE - " + payload["email"])

@public
def token_login(request):
    print("Processing Token")
    print(request.META)
    return HttpResponse("Success!")

@public
def token_redirect(request):

    redirect_response = HttpResponseRedirect('http://localhost:8001/tokenlogin/token_login/')
    redirect_response['Authorization'] = 'Bearer ***REMOVED***'
    redirect_response['TESTHEADERS'] = 'TESTHEADERS'

    return render(request, 'tokenlogin/token_redirect.html')


@public
def login_done(request):
    return HttpResponse("Done logging in.")


def landing_page(request):
    return HttpResponse("Landed.")
