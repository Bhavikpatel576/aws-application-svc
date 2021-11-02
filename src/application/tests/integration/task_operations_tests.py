import datetime
import os
from pathlib import Path
from unittest.mock import patch

from django.db.utils import IntegrityError
from parameterized import parameterized
from rest_framework.test import APITestCase

from application.models.acknowledgement import Acknowledgement
from application.models.address import Address
from application.models.application import (Application, ApplicationStage,
                                            ProductOffering)
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.disclosure import Disclosure, DisclosureType
from application.models.models import CurrentHomeImage
from application.models.real_estate_agent import RealEstateAgent
from application.models.task import Task
from application.models.task_name import TaskName
from application.models.task_progress import TaskProgress
from application.models.task_status import TaskStatus
from application.task_operations import (existing_property_status,
                                         homeward_mortgage_status,
                                         photo_upload_status,
                                         run_task_operations,
                                         update_application_tasks)
from application.tasks import convert_response_to_application
from application.tests.random_objects import (random_application,
                                              random_current_home)

TITLE_TEXAS = "homeward title (texas)"
MORTGAGE_COLORADO = "homeward mortgage (colorado)"


class TaskOperationsTests(APITestCase):
    def setUp(self):
        self.sf_patch = patch("application.tasks.push_to_salesforce")
        self.sf_patch.start()
        self.addCleanup(self.sf_patch.stop)
        Disclosure.objects.update_or_create(name=TITLE_TEXAS, buying_state='tx',
                                            selling_state='tx', disclosure_type=DisclosureType.TITLE,
                                            document_url='someurl.com', active=True)
        Disclosure.objects.update_or_create(name=MORTGAGE_COLORADO,
                                            disclosure_type=DisclosureType.MORTGAGE, buying_state='co',
                                            selling_state=None, document_url='someurl.com', active=True)
    module_dir = str(Path(__file__).parent)

    # Putting these in a dictionary so string keys can be passed into parameterized tests
    payloads = {
        'FULL': open(os.path.join(module_dir, '../static/full_payload_buy_texas.json')).read(),
        'PROPERTY_COMPLETE_OUTSIDE_TEXAS': open(
            os.path.join(module_dir, '../static/existing_property_complete_outside_texas.json')).read(),
        'PROPERTY_COMPLETE': open(os.path.join(module_dir, '../static/existing_property_complete.json')).read(),
        'CREATE': open(os.path.join(module_dir, '../static/create_then_update/create.json')).read(),
        'AGENT_COMPLETE': open(os.path.join(module_dir, '../static/real_estate_agent_complete.json')).read(),
    }

    @parameterized.expand([
        ('adds only universal tasks', 'CREATE', 2, True),
        ('does not add inactive tasks', 'CREATE', 2, False),
        ('adds disclosures task', 'FULL', 5, True),
        ('adds home to sell tasks', 'PROPERTY_COMPLETE_OUTSIDE_TEXAS', 4, True)
    ])
    def test_should_add_new_tasks(self, test_name, test_type, expected_number_tasks, better_is_active):
        better = Task.objects.get(name=TaskName.MY_LENDER_BETTER)
        better.active = better_is_active
        better.save()
        self.assertEqual(TaskStatus.objects.all().count(), 0)
        convert_response_to_application(self.payloads[test_type])
        self.assertEqual(TaskStatus.objects.all().count(), expected_number_tasks)

    @parameterized.expand([
        ('agents exist', TaskProgress.NOT_STARTED, TaskProgress.COMPLETED, 'yes'),
        ('agents needed', TaskProgress.NOT_STARTED, TaskProgress.COMPLETED, 'no'),
        ('agent needed', TaskProgress.NOT_STARTED, TaskProgress.COMPLETED, 'needs one'),
        ('no agents', TaskProgress.NOT_STARTED, TaskProgress.NOT_STARTED, '')
    ])
    def test_should_update_real_estate_task(self, test_name, initial_expected_status, expected_status, agent_status):
        convert_response_to_application(self.payloads['CREATE'])

        application = Application.objects.latest('created_at')

        agent = RealEstateAgent.objects.create(name='some agent', email='someagent@realestate.com',
                                               phone='121-121-1212')

        status = TaskStatus.objects.get(application=application, task_obj__name=TaskName.REAL_ESTATE_AGENT)

        if agent_status == 'yes':
            application.listing_agent = agent
            application.buying_agent = agent
        elif agent_status == 'no':
            application.needs_buying_agent = True
            application.needs_listing_agent = True
        elif agent_status == 'needs one':
            application.needs_listing_agent = True
            application.buying_agent = agent
        application.save()
        self.assertEqual(status.status, initial_expected_status)
        update_application_tasks(application)
        status = TaskStatus.objects.get(application=application, task_obj__name=TaskName.REAL_ESTATE_AGENT)

        self.assertEqual(status.status, expected_status)

    def test_adds_appropriate_amount_of_new_tasks_on_update(self):
        convert_response_to_application(self.payloads['CREATE'])

        application = Application.objects.latest('created_at')
        task_statuses = application.task_statuses.all()

        self.assertEqual(task_statuses.count(), 2)

        address = Address.objects.create(street='1234 S Lamar Blvd', city='Austin', state='TX', zip='78704')
        application.current_home = CurrentHome.objects.create(address=address)
        application.save()

        run_task_operations(application)

        existing_property_status = TaskStatus.objects.filter(application=application,
                                                             task_obj__name=TaskName.EXISTING_PROPERTY)
        task_statuses = application.task_statuses.all()

        self.assertEqual(task_statuses.count(), 4)
        self.assertEqual(existing_property_status.count(), 1)

    def test_existing_property_task_status_transitions(self):
        convert_response_to_application(self.payloads['CREATE'])

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)

        address = Address.objects.create(street='1234 S Lamar Blvd', city='Austin', state='TX', zip='78704')
        application.current_home = CurrentHome.objects.create(address=address)

        self.assertEqual(existing_property_status(application), TaskProgress.NOT_STARTED)

        application.current_home.customer_value_opinion = '234523'

        application.current_home.save()

        self.assertEqual(existing_property_status(application), TaskProgress.COMPLETED)

        application.current_home.customer_value_opinion = None

        application.current_home.listing_status = "Under Contract"

        application.current_home.save()

        self.assertEqual(existing_property_status(application), TaskProgress.COMPLETED)

        application.current_home.listing_status = None

        application.current_home.save()
        
        self.assertEqual(existing_property_status(application), TaskProgress.NOT_STARTED)

        application.current_home.listing_status = "Listed"

        application.current_home.save()
        
        self.assertEqual(existing_property_status(application), TaskProgress.COMPLETED)



    def test_photos_task_status_transitions(self):
        convert_response_to_application(self.payloads['CREATE'])

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)

        self.assertEqual(application.stage, ApplicationStage.INCOMPLETE)

        self.assertEqual(photo_upload_status(application), TaskProgress.COMPLETED)

        address = Address.objects.create(street='1234 S Lamar Blvd', city='Austin', state='TX', zip='78704')
        home = CurrentHome.objects.create(address=address)
        application.current_home = home

        self.assertEqual(photo_upload_status(application), TaskProgress.NOT_STARTED)


        application.current_home.listing_status = "Under Contract"

        application.current_home.save()

        self.assertEqual(photo_upload_status(application), TaskProgress.COMPLETED)

        application.current_home.listing_status = None

        application.current_home.save()
        
        self.assertEqual(photo_upload_status(application), TaskProgress.NOT_STARTED)

        application.current_home.listing_status = "Listed"

        application.current_home.save()
        
        self.assertEqual(photo_upload_status(application), TaskProgress.COMPLETED)

        CurrentHomeImage.objects.create(current_home=home, url='a')

        application.current_home.listing_status = None

        application.current_home.save()

        self.assertEqual(photo_upload_status(application), TaskProgress.IN_PROGRESS)

        for n in range(5):
            CurrentHomeImage.objects.create(current_home=home, url=str(n))

        self.assertEqual(photo_upload_status(application), TaskProgress.COMPLETED)
        for status in application.task_statuses.all():
            status.status = TaskProgress.COMPLETED
            status.save()
        application.save()
        self.assertEqual(application.stage, ApplicationStage.COMPLETE)

    def test_acknowledgements_status(self):
        convert_response_to_application(self.payloads['CREATE'])

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)
        disclosure = Disclosure.objects.create(name="blah", document_url="http://blah.com", active=True)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=disclosure)
        other_acknowledgement = Acknowledgement.objects.create(application=application, disclosure=disclosure)

        # create the task the fun way
        run_task_operations(application)

        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.DISCLOSURES).status,
                         TaskProgress.NOT_STARTED.value)

        acknowledgement.is_acknowledged = True
        acknowledgement.save()
        run_task_operations(application)

        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.DISCLOSURES).status,
                         TaskProgress.IN_PROGRESS.value)

        other_acknowledgement.is_acknowledged = True
        other_acknowledgement.save()
        run_task_operations(application)

        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.DISCLOSURES).status,
                         TaskProgress.COMPLETED.value)

    def test_homeward_mortgage_task(self):
        convert_response_to_application(self.payloads['CREATE'])

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)
        application.home_buying_location.state = 'CO'
        mortgage_task = Task.objects.get(name=TaskName.COLORADO_MORTGAGE)
        application.save()

        mortgage_task.active = False
        mortgage_task.start_date = datetime.date.today() - datetime.timedelta(days=7)
        mortgage_task.save()

        run_task_operations(application)

        with self.assertRaises(Exception):
            application.task_statuses.get(task_obj__name=TaskName.COLORADO_MORTGAGE)

        mortgage_task.active = True
        mortgage_task.end_date = datetime.date.today() - datetime.timedelta(days=1)
        mortgage_task.save()
        run_task_operations(application)
        with self.assertRaises(Exception):
            application.task_statuses.get(task_obj__name=TaskName.COLORADO_MORTGAGE)

        mortgage_task.active = True
        mortgage_task.end_date = datetime.date.today() + datetime.timedelta(days=1)
        mortgage_task.save()

        run_task_operations(application)
        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.COLORADO_MORTGAGE).status,
                         TaskProgress.NOT_STARTED)

    def test_application_stage_doesnt_care_about_mortgage_task(self):
        convert_response_to_application(self.payloads['FULL'])

        application = Application.objects.latest('created_at')
        application.task_statuses.all().update(status=TaskProgress.COMPLETED)
        TaskStatus.objects.create(application=application, task_obj=Task.objects.get(name=TaskName.COLORADO_MORTGAGE),
                                  status=TaskProgress.IN_PROGRESS)

        self.assertEqual(application.are_all_tasks_complete(), True)

    def test_task_status_unique_constraint(self):
        convert_response_to_application(self.payloads['FULL'])
        application = Application.objects.latest('created_at')
        TaskStatus.objects.create(application=application, task_obj=Task.objects.get(name=TaskName.COLORADO_MORTGAGE),
                                  status=TaskProgress.IN_PROGRESS)

        with self.assertRaises(IntegrityError):
            TaskStatus.objects.create(application=application,
                                      task_obj=Task.objects.get(name=TaskName.COLORADO_MORTGAGE),
                                      status=TaskProgress.IN_PROGRESS)

    @parameterized.expand([
        ('no blend status', None, TaskProgress.NOT_STARTED),
        ('blank blend status', '', TaskProgress.NOT_STARTED),
        ('lowercase started status', 'application created', TaskProgress.IN_PROGRESS),
        ('uppercase started status', 'APPLICATION CREATED', TaskProgress.IN_PROGRESS),
        ('in progress status pattern', 'Application in progress: msfkvjtgrt', TaskProgress.IN_PROGRESS),
        ('lowercase archived application status', 'APPLICATION ARCHIVED', TaskProgress.IN_PROGRESS),
        ('uppercase archived application status', 'application archived', TaskProgress.IN_PROGRESS),
        ('lowercase complete status', 'application completed (borrower submit)', TaskProgress.COMPLETED),
        ('uppercase complete status', 'APPLICATION COMPLETED (BORROWER SUBMIT)', TaskProgress.COMPLETED),
        ('uppercase TRID complete status', 'APPLICATION COMPLETED (TRID TRIGGERED)', TaskProgress.COMPLETED),
        ('lowercase TRID complete status', 'application completed (trid triggered)', TaskProgress.COMPLETED),
        ('error status', 'BLAH BLAH BLAH', TaskProgress.UNDER_REVIEW)
    ])
    def test_blend_status_parsing_case_insensitive(self, test_case, blend_status, expected_task_status):
        convert_response_to_application(self.payloads['FULL'])
        application = Application.objects.latest('created_at')
        application.blend_status = blend_status
        application.stage = ApplicationStage.APPROVED

        mortgage_task_progress = homeward_mortgage_status(application)
        self.assertEquals(mortgage_task_progress, expected_task_status)

    def test_should_remove_current_home_tasks_for_buy_only(self):
        app = random_application(current_home=random_current_home(), product_offering=ProductOffering.BUY_SELL)
        
        run_task_operations(app)

        self.assertTrue(app.task_statuses.filter(task_obj__name=TaskName.PHOTO_UPLOAD).exists())
        self.assertTrue(app.task_statuses.filter(task_obj__name=TaskName.EXISTING_PROPERTY).exists())

        app.product_offering = ProductOffering.BUY_ONLY
        app.save()

        run_task_operations(app)

        self.assertFalse(app.task_statuses.filter(task_obj__name=TaskName.PHOTO_UPLOAD).exists())
        self.assertFalse(app.task_statuses.filter(task_obj__name=TaskName.EXISTING_PROPERTY).exists())
