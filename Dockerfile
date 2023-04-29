FROM python:3.11.3-slim-buster

ADD main.py helpers.py requirements.txt /

RUN pip install -r requirements.txt && \
    rm requirements.txt

CMD [ "python3", "./main.py" ]