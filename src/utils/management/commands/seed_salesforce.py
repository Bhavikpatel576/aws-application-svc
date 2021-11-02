import os
import logging
import inspect

from django.core.management.base import BaseCommand
from faker import Faker
from application.tests import random_objects
from application.models.application import Application, ApplicationStage, LeadStatus
from application.models.task_progress import TaskProgress
from src.application.tests.random_objects import random_current_home
from utils.salesforce import homeward_salesforce, Salesforce, SalesforceObjectType
from datetime import datetime


fake = Faker()
APP_ENV = os.environ.get('APP_ENV', 'test')
logger = logging.getLogger(__name__)
class Command(BaseCommand):
    help = """Creates tests data in Salesforce and Application-SVC"""

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--email',
            type=str,
            help='Enter an email address for testing data',
        )

    def handle(self, *args, **options):
        if APP_ENV != 'stage': raise Exception('This script should only be run in our staging environment')
        """ run SeedSalesforceTest """
        email_address = options['email'] or fake.email()
        class_to_run = SeedSalesforce(email=email_address)
        attrs = (getattr(class_to_run, name) for name in dir(class_to_run))
        methods = filter(inspect.ismethod, attrs)
        for method in methods:
            try:
                method()
            except TypeError:
                # Can't handle methods with required arguments.
                pass

class SeedSalesforce():
    
    def __init__(self, email) -> None:
        self.homeward_salesforce: Salesforce = homeward_salesforce
        parts_of_email = email.split('@')
        if (len(parts_of_email) < 2): raise Exception('invalid email address')
        self.email_username = parts_of_email[0]

    def create_salesforce_account_object(self) -> None:
        data = {"name": "__APP_SVC_TEST_ACCOUNT__"}
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=SalesforceObjectType.ACCOUNT)
        logger.info("create_salesforce_account_object", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id ))


    def create_salesforce_transaction_object(self) -> None:
        """ create a transaction """
        # create a customer
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        account_data = random_objects.random_customer(customer_email=customer_email_address)
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(account_data.to_salesforce_representation(), object_type=SalesforceObjectType.ACCOUNT)
        
        # required fields for a transaction
        data = { "Customer__c": sales_force_account_id, "New_Home_Offer_Price__c": 299999 }
        sales_force_transaction_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=SalesforceObjectType.TRANSACTION)
        logger.info("create_salesforce_transaction_object", extra=dict(type='create_new_salesforce_object', return_value=sales_force_transaction_id, email_address=customer_email_address ))

    def create_salesforce_offer_object(self) -> None:
        # create offer dependencies 
        app = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                current_home=random_objects.random_current_home(floor_price=random_objects.random_floor_price())
                                                )
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(app.to_salesforce_representation(), object_type=app.salesforce_object_type())
        # save sf id to application
        app.new_salesforce = sales_force_account_id
        app.save()
        # create offer and set required fields
        offer = random_objects.random_offer(application=app)
        offer.already_under_contract = True
        offer.waive_appraisal = 'Yes' #update to use enum
        offer.save()
        # push offer to sf
        offer.attempt_push_to_salesforce()
        logger.info("create_salesforce_offer_object", extra=dict(type='create_new_salesforce_object', return_value=offer.salesforce_id, app=app.__dict__ ))


    def create_customer_and_agent(self) -> None:
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        """ create a customer and a linked buying agent """
        current_home = random_objects.random_current_home()
        # create an application for the customer
        app: Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address), current_home=current_home)
        # create agent and add to application
        agent_email_address = f'{self.email_username}+agent{time}@homeward.com'
        buying_agent = random_objects.random_agent(agent_email=agent_email_address)
        app.buying_agent = buying_agent
        app.save()
        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_and_agent", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
    

    def create_customer_incomplete_application(self) -> None:
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        """ create a customer that does not finish tasks """
        # create an application for the customer
        app:Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address))
        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_incomplete_application", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
    

    def create_customer_completed_tasks(self) -> None:
        """ create a customer that has completed all tasks  """
        # create an application for the customer
        app: Application = Application.objects.create(customer=random_objects.random_customer())
        # update application so all tasks are completed
        app.task_statuses.all().update(status=TaskProgress.COMPLETED)
        app.save()
        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_completed_tasks", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
    

    def create_customer_qualified_application(self) -> None:
        """ create a customer with an application stage set to qualified  """
        # create an application for the customer
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        app: Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address))

        # set application stage to qualified
        app.stage = ApplicationStage.QUALIFIED_APPLICATION

        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_qualified_application", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
    

    def create_customer_approved_application(self) -> None:
        """ create a customer with an application stage set to approved  """
        # create an application for the customer
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        app: Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address))

        # update application fields required for approval
        app.estimated_down_payment = '10000'
        app.lender_pre_approval_amount = '100000'
        app.adjusted_avm = '100000'
        app.floor_price = '0'
        app.old_home_approved_purchase_price = 'Yes'
        app.lead_status = LeadStatus.QUALIFIED
        app.cx_assigned = 'John Jackson'
        app.stage = ApplicationStage.APPROVED

        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_approved_application", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))


    def create_customer_denied_application(self) -> None:
        """ create a customer with an application stage set to denied  """
        # create an application for the customer
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        app: Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address))

        # set application stage to denied
        app.stage = ApplicationStage.DENIED

        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_denied_application", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
    

    def create_customer_application_buy_before_you_sell(self) -> None:
        """ create a customer with an application with a current home  """
        # create an application for the customer with a current home
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        app: Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address), current_home=random_current_home())

        # update application fields required for approval
        app.estimated_down_payment = '10000'
        app.lender_pre_approval_amount = '100000'
        app.adjusted_avm = '100000'
        app.floor_price = '0'
        app.old_home_approved_purchase_price = 'Yes'
        app.lead_status = LeadStatus.QUALIFIED
        app.cx_assigned = 'John Jackson'
        app.stage = ApplicationStage.INCOMPLETE

        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_application_buy_before_you_sell", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
    

    def create_customer_approved_buy_with_cash(self) -> None:
        """ create a customer with no current home and an application stage set to approved  """
        # create an application for the customer
        time = datetime.now().strftime('%m-%d-%h-%m-%s')
        customer_email_address = f'{self.email_username}+{time}@homeward.com'
        app: Application = Application.objects.create(customer=random_objects.random_customer(customer_email=customer_email_address))

        # update application fields required for approval
        app.estimated_down_payment = '10000'
        app.lender_pre_approval_amount = '100000'
        app.adjusted_avm = '100000'
        app.floor_price = '0'
        app.old_home_approved_purchase_price = 'Yes'
        app.lead_status = LeadStatus.QUALIFIED
        app.cx_assigned = 'John Jackson'
        app.stage = ApplicationStage.APPROVED

        # send data to SF
        data = app.to_salesforce_representation()
        sales_force_account_id = self.homeward_salesforce.create_new_salesforce_object(data, object_type=app.salesforce_object_type())
        logger.info("create_customer_approved_buy_with_cash", extra=dict(type='create_new_salesforce_object', return_value=sales_force_account_id, sf_data=data ))
