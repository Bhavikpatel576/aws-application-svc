import logging

from django.core.management.base import BaseCommand

from application.application_acknowledgements import create_service_agreement
from application import constants
from application.models.application import Application, ApplicationStage
from application.models.task_category import TaskCategory
from application.models.task_name import TaskName
from application.task_operations import add_task_if_active, disclosures_status


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Creates acknowledgements for new service agreement (June 2021) and applications with disclosures
    that have been acknowledged up to the option period stage"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--all_applications',
            action='store_true',
            help='This flag will add acknowledgements to all applications, not just those with homeward emails',
        )

    def handle(self, *args, **options):
        no_state = 0
        total_updated = 0

        application_stages_to_target = [ApplicationStage.INCOMPLETE,
                                        ApplicationStage.COMPLETE,
                                        ApplicationStage.QUALIFIED_APPLICATION,
                                        ApplicationStage.FLOOR_PRICE_REQUESTED,
                                        ApplicationStage.FLOOR_PRICE_COMPLETED,
                                        ApplicationStage.APPROVED,
                                        ApplicationStage.DENIED,
                                        ApplicationStage.OFFER_REQUESTED,
                                        ApplicationStage.OFFER_SUBMITTED]

        service_agreements_to_exclude = [constants.SERVICE_AGREEMENT_TX,
                                         constants.SERVICE_AGREEMENT_TX_BUY_ONLY,
                                         constants.SERVICE_AGREEMENT_TX_RA,
                                         constants.SERVICE_AGREEMENT_TX_RA_BUY_ONLY,
                                         constants.SERVICE_AGREEMENT_CO,
                                         constants.SERVICE_AGREEMENT_CO_BUY_ONLY,
                                         constants.SERVICE_AGREEMENT_GA,
                                         constants.SERVICE_AGREEMENT_GA_BUY_ONLY]

        # applications in specified stage that do not have a new service agreement acknowledgement
        targeted_applications = Application.objects.filter(stage__in=application_stages_to_target)
        applications_without_acknowledgement = targeted_applications.exclude(acknowledgements__disclosure__name__in=service_agreements_to_exclude)

        # default filter to homeward emails only
        if not options['all_applications']:
            print('homeward emails only')
            applications_without_acknowledgement = applications_without_acknowledgement.filter(customer__email__regex=r'\+.+@homeward.com')

        print(f'found {applications_without_acknowledgement.count()} applications')

        for application in applications_without_acknowledgement:
            buying_state = application.get_purchasing_state()

            if buying_state:
                buying_state = buying_state.lower()
            else:
                no_state += 1
                print(f'No state found for {application.id}')
                continue

            buying_agent_brokerage = application.get_buying_agent_brokerage_name()

            print(f'Creating service agreement for {application.id}')
            create_service_agreement(application, buying_state, buying_agent_brokerage)

            print(f'Run task operations for {application.id}')
            add_task_if_active(application=application, name=TaskName.DISCLOSURES)
            task_status = application.task_statuses.get(task_obj__category=TaskCategory.DISCLOSURES)
            updated_status = disclosures_status(application)
            task_status.status = updated_status
            task_status.save()

            print(f'service agreement added and task reopened for {application.id}')
            total_updated += 1

        print(f'No states: {no_state}')
        print(f'Total updated: {total_updated}')
