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

#point to stage
default_connection = dj_database_url.parse('postgresql://postgres:docker@host.docker.internal:5432/application-service')
default_connection.update({'CONN_MAX_AGE': 600, })
DATABASES = {
    'default': default_connection,
}
CELERY_BROKER_URL = ''

CELERY_BACKEND = ''

CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_DEFAULT_QUEUE = 'application-service-tasks'

CLOUDAMQP_URL = ''

CAS_SERVER_URL = 'http://localhost:8000/cas/login' #update to stage

# salesforce
# point to HWFULL
NEW_SALESFORCE = {
    "username": "api.user@homeward.com.hwtest2",
    "password": "hx%uu!4AsWfG1",
    "domain": "test",
    "security_token": "UZfebF0ItHxgDZ50TzBETyAm4"
}

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
HOMEWARD_SSO_BASE_URL = 'http://localhost:5000/'
HOMEWARD_SSO_AUTH_TOKEN = 'LLT e718b5a780733b7f24d181e04c0d53301897092c'

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
    'loggers': {
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    }
}

HOMEWARD_OAUTH_BASE_URL = 'https://homeward-oauth-stage.herokuapp.com/'
APPLICATION_SERVICE_CLIENT_ID = 'id'
APPLICATION_SERVICE_CLIENT_SECRET = 'secret'
PROPERTY_DATA_AGGREGATOR_BASE_ENDPOINT = 'https://property-data-aggregator-stage.herokuapp.com/'
AGENT_SERVICE_BASE_ENDPOINT = 'https://agent-service-stage.herokuapp.com/'

PARTNER_BRANDING_CONFIG_URL = 'https://partner-branding-config-stage.herokuapp.com/'

USE_NEW_PRICING_UPDATES = True
VALIDATE_PREFERRED_CLOSING_DATE = True
LOG_REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
GENERATE_REQUEST_ID_IF_NOT_IN_HEADER = True
LOG_REQUESTS = True
