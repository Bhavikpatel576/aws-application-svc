"""
Production environment settings.
"""

import json
import os
import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

APP_ENV = os.environ.get('APP_ENV', 'test')

DEBUG = bool(os.environ.get("DEBUG", "false").lower() == "true")
SECRET_KEY = os.environ.get("SECRET_KEY")

DEFAULT_CONNECTION = dj_database_url.parse(os.environ.get("DATABASE_URL"))
DEFAULT_CONNECTION.update({"CONN_MAX_AGE": 600})
DATABASES = {"default": DEFAULT_CONNECTION}

ALLOWED_HOSTS = json.loads(os.environ.get("ALLOWED_HOSTS", "[\"*\"]"))


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")

CELERY_BACKEND = os.environ.get("CELERY_BACKEND")

CELERY_TASK_DEFAULT_QUEUE = 'application-service-tasks'

CLOUDAMQP_URL = os.environ.get("CLOUDAMQP_URL")

CAS_SERVER_URL = os.environ.get('CAS_SERVER_URL')

# salesforce
NEW_SALESFORCE = json.loads(os.environ.get("NEW_SALESFORCE", "{}").replace('\'', '\"'))

HUBSPOT = {
    'API_KEY': os.environ.get('HUBSPOT_API_KEY'),
    'URL': os.environ.get('HUBSPOT_URL'),
    'HUB_ID': os.environ.get('HUBSPOT_HUB_ID'),
    'FORM_GUID': os.environ.get('HUBSPOT_GUID'),
    'FORM_URL': os.environ.get('HUBSPOT_FORM_URL'),
}

BLEND = {
    'BASE_URL': os.environ.get('BLEND_BASE_URL'),
    'API_KEY': os.environ.get('BLEND_API_KEY'),
    'API_VERSION': os.environ.get('BLEND_API_VERSION'),
    'TARGET_INSTANCE': os.environ.get('BLEND_TARGET_INSTANCE'),
    'POLLING_TIME': os.environ.get('BLEND_POLLING_TIME'),
    'BLEND_MAX_RETRIES': os.environ.get('BLEND_MAX_RETRIES'),
    'FOLLOWUP_SALESFORCE_RETRIES': os.environ.get('FOLLOWUP_SALESFORCE_RETRIES')
}

FRONTEND_APPLICATION_OVERVIEW_URL = os.environ.get('FRONTEND_APPLICATION_OVERVIEW_URL')

ADMIN_HEADER = os.environ.get('ADMIN_HEADER', 'CRM service admin')

AWS = {
    'SECRET_KEY': os.environ.get('AWS_SECRET_KEY'),
    'ACCESS_KEY': os.environ.get('AWS_ACCESS_KEY'),
    'BUCKET': os.environ.get('AWS_BUCKET'),
    'S3_CUSTOM_DOMAIN': '{}.s3.amazonaws.com'.format(os.environ.get('AWS_BUCKET')),
    'REGION_NAME': os.environ.get('AWS_REGION_NAME'),
    'HOMEWARD_CONTRACTS_SECRET_KEY': os.environ.get('AWS_HOMEWARD_CONTRACTS_SECRET_KEY'),
    'HOMEWARD_CONTRACTS_ACCESS_KEY': os.environ.get('AWS_HOMEWARD_CONTRACTS_ACCESS_KEY'),
}

PHOTO_UPLOAD_NOTIFICATION_EMAIL = os.environ.get('PHOTO_UPLOAD_NOTIFICATION_EMAIL')

if APP_ENV in ['prod', 'stage']:
    sentry_sdk.init(
        environment=APP_ENV,
        dsn="https://0d801a7f733b4464b703ecaf7b5b21ed@sentry.io/1520289",
        integrations=[DjangoIntegration(), CeleryIntegration()]
    )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'add_log_level': {'()': 'core.settings.logging.AddSeverityLevel'},
        'request_id': {'()': 'log_request_id.filters.RequestIDFilter'}
    },
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(levelname)s %(asctime)s %(request_id)s %(name)s %(pathname)s %(funcName)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['add_log_level', 'request_id'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DEBUG_LEVEL', 'WARNING'),
    },
}

ONBOARDING_BASE_URL = os.environ.get('ONBOARDING_BASE_URL', 'https://app.homeward.com/')
APEX_ONBOARDING_BASE_URL = os.environ.get('APEX_ONBOARDING_BASE_URL', 'https://app.buywithcash.com/')

USE_NEW_PRICING_UPDATES = os.environ.get('USE_NEW_PRICING_UPDATES', False)

HOMEWARD_SSO_BASE_URL = os.environ.get('HOMEWARD_SSO_BASE_URL', '')
HOMEWARD_SSO_AUTH_TOKEN = os.environ.get('HOMEWARD_SSO_AUTH_TOKEN', '')

CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", False)

HOMEWARD_OAUTH_BASE_URL = os.environ.get("HOMEWARD_OAUTH_BASE_URL")
APPLICATION_SERVICE_CLIENT_ID = os.environ.get("APPLICATION_SERVICE_CLIENT_ID")
APPLICATION_SERVICE_CLIENT_SECRET = os.environ.get("APPLICATION_SERVICE_CLIENT_SECRET")
PROPERTY_DATA_AGGREGATOR_BASE_ENDPOINT = os.environ.get("PROPERTY_DATA_AGGREGATOR_BASE_ENDPOINT")
AGENT_SERVICE_BASE_ENDPOINT = os.environ.get("AGENT_SERVICE_BASE_ENDPOINT")
PARTNER_BRANDING_CONFIG_URL = os.environ.get("PARTNER_BRANDING_CONFIG_URL")

VALIDATE_PREFERRED_CLOSING_DATE = os.environ.get("VALIDATE_PREFERRED_CLOSING_DATE", True)
