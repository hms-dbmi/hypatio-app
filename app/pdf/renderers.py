from django.template import loader

from .generators import PDFGenerator


def render_pdf(filename, request, template_name, context=None, using=None, options={}):

    # Render to file.
    content = loader.render_to_string(template_name, context, request, using=using)
    pdf = PDFGenerator(content, **options)

    return pdf.get_http_response(filename)
