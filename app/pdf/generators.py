import subprocess
import os
import random

from .settings import pdf_settings
from django.http import HttpResponse
from django.core.files.base import ContentFile


class PDFGenerator(object):
    def __init__(self, html, paperformat='A4', zoom=1, script=pdf_settings.DEFAULT_RASTERIZE_SCRIPT,
                 temp_dir=pdf_settings.DEFAULT_TEMP_DIR):
        self.script = script
        self.temp_dir = temp_dir
        self.html = html
        self.html_file = self.__get_html_filepath()
        self.pdf_file = self.__get_pdf_filepath()
        self.paperformat = paperformat
        self.zoom = zoom
        self.pdf_data = None

        self.__write_html()
        self.__generate()
        self.__set_pdf_data()
        self.__remove_source_file()

    def __write_html(self):
        with open(self.html_file, 'w') as f:
            f.write(self.html)
            f.close()

    def __get_html_filepath(self):
        return os.path.join(self.temp_dir, '{}.html'.format(PDFGenerator.get_random_filename(25)))

    def __get_pdf_filepath(self):
        return os.path.join(self.temp_dir, '{}.pdf'.format(PDFGenerator.get_random_filename(25)))

    def __generate(self):
        """
        call the following command:
            phantomjs rasterize.js URL filename [paperwidth*paperheight|paperformat] [zoom]
        """
        phantomjs_env = os.environ.copy()
        phantomjs_env["OPENSSL_CONF"] = "/etc/openssl/"
        command = [
            pdf_settings.PHANTOMJS_BIN_PATH,
            '--ssl-protocol=any',
            '--ignore-ssl-errors=yes',
            self.script,
            self.html_file,
            self.pdf_file,
            self.paperformat,
            str(self.zoom)
        ]
        return subprocess.call(command, env=phantomjs_env)

    def __set_pdf_data(self):
        with open(self.pdf_file, "rb") as pdf:
            self.pdf_data = pdf.read()

    def get_content_file(self, filename):
        return ContentFile(self.pdf_data, name=filename)

    def get_data(self):
        return self.pdf_data

    def get_http_response(self, filename):
        response = HttpResponse(self.pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}.pdf"'.format(filename)
        return response

    def __remove_source_file(self):
        html_rm = subprocess.call(['rm', self.html_file])
        pdf_rm = subprocess.call(['rm', self.pdf_file])
        return html_rm & pdf_rm

    @staticmethod
    def get_random_filename(nb=50):
        choices = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join([random.choice(choices) for _ in range(nb)])
