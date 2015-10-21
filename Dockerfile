FROM eeacms/python:2.7-slim

#Install requirements
RUN mkdir ldaplog
COPY requirements.txt requirements-dev.txt /ldaplog/
WORKDIR ldaplog

RUN pip install -U setuptools
RUN pip install -r requirements-dev.txt

#Copy code
COPY ldaplog/ ./ldaplog
COPY setup.py ./setup.py

EXPOSE 8000

CMD env python ldaplog/manage.py tornado -p 8000
