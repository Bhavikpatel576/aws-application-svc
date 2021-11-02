from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from celery.signals import setup_logging

# set the default Django settings module for the 'celery' program.
from event_consumer.handlers import AMQPRetryConsumerStep

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('utils', broker=settings.CELERY_BROKER_URL,
             backend=settings.CELERY_BACKEND)
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)


app.steps['consumer'].add(AMQPRetryConsumerStep)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
