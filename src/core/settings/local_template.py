"""
Local environment settings.
"""

import dj_database_url

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'w^&*p9y_h7w0x_)q2ho0%rbzs)u^^iwceeyb&coe_a#7zhxf7%'

DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

default_connection = dj_database_url.parse('postgresql://postgres:docker@localhost:5432/application-service')
default_connection.update({'CONN_MAX_AGE': 600, })
DATABASES = {
    'default': default_connection,
}
CELERY_BROKER_URL = ''

CELERY_BACKEND = ''

CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_DEFAULT_QUEUE = 'application-service-tasks'

CLOUDAMQP_URL = ''

CAS_SERVER_URL = ''

# salesforce
NEW_SALESFORCE = {}

HUBSPOT = {
    'API_KEY': '',
    'URL': '',
    'HUB_ID': '',
    'FORM_GUID': '',
    'FORM_URL': '',
}

BLEND = {
    'BASE_URL': 'https://api.beta.blendlabs.com',
    'API_KEY': '=',
    'API_VERSION': '4.1.0',
    'TARGET_INSTANCE': 'homeward~default',
    'POLLING_TIME': 24,
    'BLEND_MAX_RETRIES': 2,
    'FOLLOWUP_SALESFORCE_RETRIES': 2
}

FRONTEND_APPLICATION_OVERVIEW_URL = 'https://homeward-crm-stage.herokuapp.com/applications/{}/overview'

APP_ENV = 'local'
ADMIN_HEADER = 'CRM service admin'

AWS = {
    'SECRET_KEY': 'AWS_SECRET_KEY',
    'ACCESS_KEY': ('AWS_ACCESS_KEY'),
    'BUCKET': ('AWS_BUCKET'),
    'S3_CUSTOM_DOMAIN': '{}.s3.amazonaws.com'.format(('AWS_S3_CUSTOM_DOMAIN')),
    'REGION_NAME': ('AWS_REGION_NAME'),
    'HOMEWARD_CONTRACTS_SECRET_KEY': 'AWS_HOMEWARD_CONTRACTS_SECRET_KEY',
    'HOMEWARD_CONTRACTS_ACCESS_KEY': 'AWS_HOMEWARD_CONTRACTS_ACCESS_KEY'
}

ONBOARDING_BASE_URL = 'https://homeward-onboarding-stage.herokuapp.com/'
APEX_ONBOARDING_BASE_URL = 'https://staging.app.buywithcash.com/'
HOMEWARD_SSO_BASE_URL = 'https://homeward-sso-stage.herokuapp.com/'
HOMEWARD_SSO_AUTH_TOKEN = ''

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

HOMEWARD_OAUTH_BASE_URL = 'https://homeward-oauth-stage.herokuapp.com/'
APPLICATION_SERVICE_CLIENT_ID = 'id'
APPLICATION_SERVICE_CLIENT_SECRET = 'secret'
PROPERTY_DATA_AGGREGATOR_BASE_ENDPOINT = 'https://property-data-aggregator-stage.herokuapp.com/'

PARTNER_BRANDING_CONFIG_URL = 'https://partner-branding-config-stage.herokuapp.com/'

USE_NEW_PRICING_UPDATES = True
VALIDATE_PREFERRED_CLOSING_DATE = True
PHOTO_UPLOAD_NOTIFICATION_EMAIL = ''
AGENT_SERVICE_BASE_ENDPOINT = 'https://agent-service-stage.herokuapp.com/'