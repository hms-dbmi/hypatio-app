import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError

import logging
logger = logging.getLogger(__name__)


class CSPReportParser(BaseParser):
    """
    Parser for application/csp-report content type.
    """
    media_type = 'application/csp-report'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming request stream as JSON and returns the resulting data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        try:
            data = stream.read().decode(encoding)
            return json.loads(data)
        except ValueError as exc:
            raise ParseError('JSON parse error - %s' % str(exc))



class CSPReportView(APIView):
    """
    A view for receiving and processing Content Security Policy (CSP) violation reports.
    """
    parser_classes = [CSPReportParser]

    def post(self, request, *args, **kwargs):
        # CSP reports usually come in the form: {"csp-report": { ... }}
        report = request.data.get("csp-report", None)
        # if report:
        #     logger.warning("CSP Violation Reported: %s", report)
        # else:
        #     logger.warning("Invalid CSP Report Received: %s", request.data)

        # Respond with 204 No Content as per best practice
        return Response(status=status.HTTP_204_NO_CONTENT)
