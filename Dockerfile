FROM dbmi/pynxgu

COPY app /app
RUN pip install -r /app/requirements.txt

RUN pip install awscli

RUN apt-get update && apt-get install -y jq

RUN mkdir /entry_scripts/
COPY gunicorn-nginx-entry.sh /entry_scripts/
RUN chmod u+x /entry_scripts/gunicorn-nginx-entry.sh

COPY hypatio.conf /etc/nginx/sites-available/pynxgu.conf

# Link nginx logs to stdout/stderr
RUN ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /dev/stderr /var/log/nginx/error.log

WORKDIR /

ENTRYPOINT ["/entry_scripts/gunicorn-nginx-entry.sh"]