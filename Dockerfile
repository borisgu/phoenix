FROM python:3.11-alpine3.17

ENV GROUP_ID=1000 \
    USER_ID=1000

WORKDIR /var/www/
RUN apk update && \
    apk add --no-cache aws-cli

ADD wsgi.py app.py kube.py helpers.py config.py requirements.txt /var/www/
RUN pip install -r requirements.txt && \
    pip install gunicorn && \
    rm requirements.txt

RUN addgroup -g $GROUP_ID www && \
    adduser -D -u $USER_ID -G www www -s /bin/sh

USER www

EXPOSE 5000

CMD [ "gunicorn", "-w", "3", "--bind", "0.0.0.0:5000", "wsgi"]
