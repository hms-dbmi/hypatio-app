from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTScheme(OpenApiAuthenticationExtension):
    target_class = 'dbmi_client.authn.DBMIModelUser'
    name = 'JWT Authentication'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': _(
                'Token-based authentication with required prefix "%s" (JWT can be viewed when logged in at https://authentication.dbmi.hms.harvard.edu/)'
            ) % "JWT"
        }
