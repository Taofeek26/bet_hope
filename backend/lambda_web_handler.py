"""
Lambda entry point for the Django web app, fronted by API Gateway REST
({proxy+} ANY route — see infrastructure/template.yaml). Translates API
Gateway REST proxy events into WSGI calls via apig-wsgi.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ENV", "production")

from apig_wsgi import make_lambda_handler  # noqa: E402
from config.wsgi import application  # noqa: E402

handler = make_lambda_handler(application, binary_support=True)
