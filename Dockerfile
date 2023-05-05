FROM python:3.11.3-slim-buster

ENV GROUP_ID=1000 \
    USER_ID=1000

WORKDIR /var/www/

ADD app.py helpers.py requirements.txt /var/www/
RUN pip install -r requirements.txt && \
    rm requirements.txt

RUN addgroup -g $GROUP_ID www && \
    adduser -D -u $USER_ID -G www www -s /bin/sh

USER www

EXPOSE 5000

CMD [ "gunicorn", "-w", "2", "--bind", "0.0.0.0:5000", "wsgi"]