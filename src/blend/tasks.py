import logging

from celery.schedules import crontab
from celery.task import periodic_task
from blend.task_operations import process_follow_up_data
from application.models.application import Application
from application.models.loan import Loan

logger = logging.getLogger(__name__)


# Server time is in UTC - crontab will run at 6am, 10am, 2pm, 6pm Central Time
@periodic_task(run_every=crontab(minute=0, hour=[11, 15, 19, 23]), options={'queue': 'application-service-tasks'})
def poll_blend_api():
    applications = Application.objects.filter(stage__in=[
        "incomplete", "complete", "qualified application", "approved", "offer requested", "offer submitted",
        "option period", "post option", "homeward purchase"
    ])
    excluded_withdrawn_application = applications.exclude(mortgage_status__icontains='withdrawn')
    loan_applications = Loan.objects.filter(
        application_id__in=excluded_withdrawn_application.values_list('id', flat=True),
        status__icontains='Application completed')
    return process_follow_up_data(loan_applications)
