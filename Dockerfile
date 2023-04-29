FROM python:3.11.3-slim-buster

RUN apt update

ADD main.py helper.py requirements.txt /

RUN pip install -r requirements.txt && \
    rm requirements.txt

CMD [ "python", "./main.py" ]