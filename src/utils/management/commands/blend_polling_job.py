from django.core.management.base import BaseCommand
from blend.task_operations import process_follow_up_data
from application.models.application import Application
from application.models.loan import Loan


class Command(BaseCommand):
    """ Run command: pipenv run python src/manage.py blend_polling_job """
    
    def handle(self, *arg, **options): 
        applications = Application.objects.filter(
        stage__in=["incomplete", "complete", "qualified application", "approved", "offer requested", "offer submitted",
                   "option period", "post option", "homeward purchase"]).values_list('id', flat=True)

        loan_applications = Loan.objects.filter(application_id__in=applications, status__icontains='Application completed')
        return process_follow_up_data(loan_applications)
