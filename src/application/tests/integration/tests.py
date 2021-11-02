import datetime
import os
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock
from unittest.mock import (patch, ANY)

from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import LeadStatus, ApplicationStage, ProductOffering
from application.models.blend_status import BlendStatus
from application.models.customer import Customer
from application.models.models import (Application)
from application.models.models import (CurrentHome, CurrentHomeImage, Address)
from application.models.pricing import Pricing
from application.models.real_estate_agent import RealEstateAgent
from application.models.task import Task
from application.models.task_category import TaskCategory
from application.models.task_name import TaskName
from application.models.task_progress import TaskProgress
from application.models.task_status import TaskStatus
from application.task_operations import run_task_operations
from application.tasks import convert_response_to_application, get_lead_source_from_hubspot
from application.tests import random_objects


class ApplicationTests(AuthMixin, APITestCase):
    def setUp(self):
        # todo get patch.multiple to work
        self.sf_patch = patch("application.tasks.push_to_salesforce")
        self.sf_patch.start()
        self.addCleanup(self.sf_patch.stop)

    module_dir = str(Path(__file__).parent)
    full_payload = open(os.path.join(module_dir, '../static/full_payload.json')).read()
    minimal_payload = open(os.path.join(module_dir, '../static/mostly_empty_payload.json')).read()
    missing_referral_source = open(os.path.join(module_dir, '../static/missing_self_reported_referral_source.json')).read()
    partial_payload = open(os.path.join(module_dir, '../static/partial_payload.json')).read()
    modified_partial_payload = open(os.path.join(module_dir, '../static/modified_partial_payload.json')).read()
    client_referral_payload = open(os.path.join(module_dir, '../static/client_referral_payload.json')).read()
    builder_referral_payload = open(os.path.join(module_dir, '../static/builder_payload.json')).read()
    lender_referral_payload = open(os.path.join(module_dir, '../static/lender_payload.json')).read()
    researching_online_application_payload = open(os.path.join(module_dir, '../static/researching_online_payload.json')).read()
    viewing_listings_payload = open(os.path.join(module_dir, '../static/viewing_listings_payload.json')).read()
    making_an_offer_payload = open(os.path.join(module_dir, '../static/making_an_offer_payload.json')).read()
    under_contract_payload = open(os.path.join(module_dir, '../static/under_contract_payload.json')).read()

    # application task status
    buying_situation_complete = open(os.path.join(module_dir, '../static/buying_situation_complete.json')).read()
    buying_situation_incomplete = open(os.path.join(module_dir, '../static/buying_situation_incomplete.json')).read()
    existing_property_incomplete = open(os.path.join(module_dir, '../static/existing_property_incomplete.json')).read()
    existing_property_complete = open(os.path.join(module_dir, '../static/existing_property_complete.json')).read()
    real_estate_agent_incomplete = open(os.path.join(module_dir, '../static/real_estate_agent_incomplete.json')).read()
    real_estate_agent_complete = open(os.path.join(module_dir, '../static/real_estate_agent_complete.json')).read()
    mortgage_preapproval_incomplete = open(
        os.path.join(module_dir, '../static/mortgage_preapproval_incomplete.json')).read()
    mortgage_preapproval_complete_no_agent = open(
        os.path.join(module_dir, '../static/mortgage_preapproval_complete_no_agent.json')).read()

    # hubspot results
    contact_payload = open(os.path.join(module_dir, '../../../utils/tests/static/hubspot_complete.json')).read()
    not_contact_payload = open(os.path.join(module_dir, '../../../utils/tests/static/hubspot_not_contact.json')).read()

    # create then update test
    create_payload = open(os.path.join(module_dir, '../static/create_then_update/create.json')).read()
    first_update_payload = open(os.path.join(module_dir, '../static/create_then_update/first_update.json')).read()
    second_update_payload = open(os.path.join(module_dir, '../static/create_then_update/second_update.json')).read()
    third_update_payload = open(os.path.join(module_dir, '../static/create_then_update/third_update.json')).read()
    fourth_update_payload = open(os.path.join(module_dir, '../static/create_then_update/fourth_update.json')).read()
    fifth_update_payload = open(os.path.join(module_dir, '../static/create_then_update/fifth_update.json')).read()
    sixth_update_payload = open(os.path.join(module_dir, '../static/create_then_update/sixth_update.json')).read()

    certified_agent_create = open(os.path.join(module_dir, '../static/certified_agent_create.json')).read()
    regular_agent_create = open(os.path.join(module_dir, '../static/regular_agent_create.json')).read()

    incomplete_referral_payload = open(os.path.join(module_dir, '../static/incomplete_referral_payload.json')).read()

    buy_only_payload = open(os.path.join(module_dir, '../static/buy_only_payload.json')).read()

    @patch("application.models.pricing.homeward_salesforce")
    @patch("application.signals.get_partner")
    def test_should_map_complete_response_to_application(self, pbc_patch, hw_sf_patch):
        hw_sf_patch.create_new_salesforce_object.return_value = random_objects.fake.pystr(max_chars=18)
        pbc_patch.return_value = {}
        random_objects.random_pricing(id="c231bf1d-0e5e-4fd0-8599-3dc16e0d69c0")
        convert_response_to_application(self.full_payload)

        brandon = Customer.objects.get(name="Brandon Kirchner")
        current_home = CurrentHome.objects.get(outstanding_loan_amount=200000)
        current_home_address = current_home.address
        application = Application.objects.get(customer=brandon)
        agent = application.real_estate_agent
        lender = application.mortgage_lender
        builder = application.builder
        images = CurrentHomeImage.objects.filter(current_home__id=current_home.id)
        making_offer_address = application.offer_property_address
        
        self.assertEqual(brandon.email, "brandon@homeward.com")
        self.assertEqual(brandon.phone, "987-987-6543")

        self.assertEqual(current_home_address.street, "1 Main Street")
        self.assertEqual(current_home_address.unit, "B")
        self.assertEqual(current_home_address.city, "Brooklyn")
        self.assertEqual(current_home_address.state, "NY")
        self.assertEqual(current_home_address.zip, "11201")

        test_date = datetime.datetime.strptime("2020-09-30", "%Y-%m-%d").date()

        self.assertEqual(current_home.customer_value_opinion, Decimal(10000000))
        self.assertEqual(current_home.listing_status, "Under Contract")
        self.assertEqual(current_home.listing_url, "https://listing-site.com/my-listing-id")
        self.assertEqual(current_home.total_concession_amount, 50000)
        self.assertEqual(current_home.option_period_expiration_date.date(), test_date)
        self.assertEqual(current_home.closing_date.date(), test_date)
        self.assertEqual(current_home.floors_count, 2)
        self.assertEqual(current_home.bedrooms_count, 4)
        self.assertEqual(current_home.master_on_main, True)
        self.assertEqual(current_home.home_size_sq_ft, 40000)
        self.assertEqual(current_home.has_made_addition, True)
        self.assertEqual(current_home.addition_type, "unpermitted addition")
        self.assertEqual(current_home.addition_size_sq_ft, 3000)
        self.assertEqual(current_home.has_basement, True)
        self.assertEqual(current_home.basement_type, "finished")
        self.assertEqual(current_home.basement_size_sq_ft, 1000)
        self.assertEqual(current_home.kitchen_countertop_type, "corian")
        self.assertEqual(current_home.kitchen_appliance_type, "stainless steel")
        self.assertEqual(current_home.kitchen_features, ['tile backsplash', 'new cabinets'])
        self.assertEqual(current_home.kitchen_has_been_remodeled, "less than 5 years ago")
        self.assertEqual(current_home.master_bathroom_condition, "some scuffs, stains, or scratches")
        self.assertEqual(current_home.full_bathrooms_count, 4)
        self.assertEqual(current_home.partial_bathrooms_count, 2)
        self.assertEqual(current_home.interior_walls_condition, "Needs some work")
        self.assertEqual(current_home.flooring_types, ["Hardwood", "Tile", "Carpet"])
        self.assertEqual(current_home.hardwood_flooring_condition, "Needs Small Repairs")
        self.assertEqual(current_home.carpet_flooring_condition, "Needs Cleaning")
        self.assertEqual(current_home.front_yard_condition, "Minimal Landscaping")
        self.assertEqual(current_home.back_yard_condition, "Basic Landscaping")
        self.assertEqual(current_home.exterior_walls_types, [
            "brick",
            "stone"
        ])
        self.assertEqual(current_home.sides_with_masonry_count, "4 side")
        self.assertEqual(current_home.roof_age_range, "5-10 years old")
        self.assertEqual(current_home.pool_type, "In-ground")
        self.assertEqual(current_home.garage_spaces_count, "3")
        self.assertEqual(current_home.hvac_age_range, "5-10 years old")
        self.assertEqual(current_home.home_features, [
            "power lines in front",
            "gated community"
        ])
        self.assertEqual(current_home.in_floodzone, "yes")
        self.assertEqual(current_home.property_view_type, "none")
        self.assertEqual(current_home.repair_or_update_detail, "I fumigated for fairies.")
        self.assertEqual(current_home.customer_notes, "Here are a bunch of notes about all the things you really need to know about this property!")
        self.assertEqual(current_home.under_contract_sales_price, None)
        self.assertEqual(current_home.anything_needs_repairs, True)
        self.assertEqual(current_home.made_repairs_or_updates, True)

        self.assertEqual(application.customer, brandon)
        self.assertEqual(application.current_home, current_home)
        self.assertEqual(application.shopping_location, "New York, NY, USA")
        self.assertEqual(application.home_buying_stage, 'working with a builder')
        self.assertEqual(application.stage, 'complete')
        self.assertEqual(application.min_price, 150000)
        self.assertEqual(application.max_price, 350000)
        self.assertEqual(application.move_in, "3-6 months")
        self.assertEqual(application.start_date.date(), datetime.date.today())
        self.assertEqual(application.lead_status, LeadStatus.NEW)
        self.assertEqual(application.self_reported_referral_source, "news_article")
        self.assertEqual(application.self_reported_referral_source_detail, "my friend told me about homeward")

        self.assertEqual(agent.name, "Tim Heyl")
        self.assertEqual(agent.phone, "9876543210")
        self.assertEqual(agent.email, "tim.heyl@homeward.com")
        self.assertEqual(agent.company, "Homeward Real Estate Inc.")
        self.assertEqual(lender.name, "Monopoly Man")
        self.assertEqual(lender.email, "banker@banks.com")
        self.assertEqual(lender.phone, "123-123-4567")

        self.assertEqual(builder.company_name, "builder company")
        self.assertEqual(builder.address.street, "4000 Danli Lane")
        self.assertEqual(builder.address.unit, "B")
        self.assertEqual(builder.address.city, "Austin")
        self.assertEqual(builder.address.state, "TX")
        self.assertEqual(builder.address.zip, "78749")
        self.assertEqual(builder.self_reported_referral_source, 'contacted by text or call')
        self.assertEqual(builder.self_reported_referral_source_detail, 'by homeward')

        self.assertEqual(making_offer_address.street, "123 Apple Blvd")
        self.assertEqual(making_offer_address.city, "New York")
        self.assertEqual(making_offer_address.state, "NY")
        self.assertEqual(making_offer_address.zip, "11202")

        self.assertEqual(application.home_buying_location.street, '12345 Alameda Trace Circle')
        self.assertEqual(application.home_buying_location.unit, '#12')
        self.assertEqual(application.home_buying_location.city, 'Austin')
        self.assertEqual(application.home_buying_location.state, 'TX')
        self.assertEqual(application.home_buying_location.zip, '78727')
        self.assertEqual(application.questionnaire_response_id, "5ea82edf-d2f9-4033-810a-1f6ac78984ba")
        self.assertEqual(application.pricing.id, uuid.UUID('c231bf1d-0e5e-4fd0-8599-3dc16e0d69c0'))
        self.assertEqual(application.agent_notes, "Client is a total whack job but hey lets see what happens")
        self.assertEqual(application.agent_client_contact_preference, "Contact agent first")
        self.assertEqual(application.apex_partner_slug, "some-apex-partner")
        self.assertEqual(application.salesforce_company_id, "some-salesforce-company-id")

    def test_should_map_minimum_possible_response_to_application(self):
        convert_response_to_application(self.minimal_payload)

        sydne = Customer.objects.get(name="Sydne Kleespies")
        application = Application.objects.get(customer=sydne)

        self.assertEqual(sydne.email, "sydne@homeward.com")
        self.assertEqual(sydne.phone, "512-512-5125")

        self.assertEqual(application.customer, sydne)
        self.assertEqual(application.shopping_location, "45645 Vía Puebla, Temecula, CA 92592, USA")
        self.assertEqual(application.home_buying_stage, 'viewing listings in person')
        self.assertEqual(application.stage, 'complete')
        self.assertEqual(application.min_price, 150000)
        self.assertEqual(application.max_price, 350000)
        self.assertEqual(application.move_in, "3-6 months")
        self.assertEqual(application.start_date.date(), datetime.date.today())

    def test_assign_none_provided_on_empty_referral_source(self):
        convert_response_to_application(self.missing_referral_source)
        sydne = Customer.objects.get(name="Sydne Kleespies")
        application = Application.objects.get(customer=sydne)
        self.assertEqual(application.self_reported_referral_source, None)

    def test_should_map_partial_response_to_application(self):
        convert_response_to_application(self.partial_payload)

        donald = Customer.objects.get(name="Donald Duck")
        application = Application.objects.get(customer=donald)
        current_home = CurrentHome.objects.get(outstanding_loan_amount=400000)
        current_home_address = current_home.address

        self.assertEqual(donald.email, "null@google.com")
        self.assertEqual(donald.phone, "345-634-5634")

        self.assertEqual(current_home_address.street, "12345 Alameda Trace Circle")
        self.assertEqual(current_home_address.city, "Austin")
        self.assertEqual(current_home_address.state, "TX")
        self.assertEqual(current_home_address.zip, "78727")

        self.assertEqual(current_home.listing_status, None)
        self.assertEqual(current_home.listing_url, None)
        self.assertEqual(current_home.total_concession_amount, None)
        self.assertEqual(current_home.option_period_expiration_date, None)
        self.assertEqual(current_home.closing_date, None)
        self.assertEqual(current_home.floors_count, 1)
        self.assertEqual(current_home.bedrooms_count, 4)
        self.assertEqual(current_home.master_on_main, False)
        self.assertEqual(current_home.home_size_sq_ft, 2000)
        self.assertEqual(current_home.has_made_addition, False)
        self.assertEqual(current_home.addition_type, None)
        self.assertEqual(current_home.addition_size_sq_ft, None)
        self.assertEqual(current_home.has_basement, None)
        self.assertEqual(current_home.basement_type, None)
        self.assertEqual(current_home.basement_size_sq_ft, None)
        self.assertEqual(current_home.kitchen_countertop_type, "quartz")
        self.assertEqual(current_home.kitchen_appliance_type, "other/don't know")
        self.assertEqual(current_home.kitchen_features, ["none of these"])
        self.assertEqual(current_home.kitchen_has_been_remodeled, "never remodeled")
        self.assertEqual(current_home.master_bathroom_condition, "needs repair")
        self.assertEqual(current_home.full_bathrooms_count, 1)
        self.assertEqual(current_home.partial_bathrooms_count, 0)
        self.assertEqual(current_home.interior_walls_condition, "Like New")
        self.assertEqual(current_home.flooring_types, ["Hardwood", "Tile"])
        self.assertEqual(current_home.hardwood_flooring_condition, "Needs Small Repairs")
        self.assertEqual(current_home.carpet_flooring_condition, None)
        self.assertEqual(current_home.front_yard_condition, None)
        self.assertEqual(current_home.back_yard_condition, None)
        self.assertEqual(current_home.exterior_walls_types, ["other/not sure"])
        self.assertEqual(current_home.sides_with_masonry_count, None)
        self.assertEqual(current_home.roof_age_range, "don't know")
        self.assertEqual(current_home.pool_type, None)
        self.assertEqual(current_home.garage_spaces_count, "0")
        self.assertEqual(current_home.hvac_age_range, "don't know")
        self.assertEqual(current_home.home_features, ["none of these"])
        self.assertEqual(current_home.in_floodzone, "no")
        self.assertEqual(current_home.property_view_type, None)
        self.assertEqual(current_home.repair_or_update_detail, None)
        self.assertEqual(current_home.customer_notes, None)
        self.assertEqual(current_home.under_contract_sales_price, None)

        self.assertEqual(application.customer, donald)
        self.assertEqual(application.shopping_location, "1231 Parkway, Austin, TX 78703, USA")
        self.assertEqual(application.home_buying_stage, 'viewing listings in person')
        self.assertEqual(application.stage, 'incomplete')
        self.assertEqual(application.min_price, 150000)
        self.assertEqual(application.max_price, 350000)
        self.assertEqual(application.move_in, "by a specific date")
        self.assertEqual(application.move_by_date, datetime.date(2019, 5, 4))
        self.assertEqual(application.start_date.date(), datetime.date.today())

    def test_updating_attributes_should_not_create_new_application(self):
        original_count = Customer.objects.count()

        convert_response_to_application(self.partial_payload)
        convert_response_to_application(self.modified_partial_payload)

        self.assertEqual(Customer.objects.count(), original_count + 1)
        self.assertEqual(CurrentHome.objects.count(), 1)
        self.assertEqual(Application.objects.count(), 1)

    def test_client_referral_payload(self):
        convert_response_to_application(self.client_referral_payload)

        jane = Customer.objects.get(name="Jane Test-client")
        application = Application.objects.get(customer=jane)
        agent = application.real_estate_agent

        self.assertEqual(jane.email, "matt.thurmond+client@gmail.com")
        self.assertEqual(jane.phone, '1-901-222-2222')
        self.assertEqual(agent.email, 'matt.thurmond@gmail.com')
        self.assertEqual(agent.company, '1984')
        self.assertEqual(agent.name, "Matt Thurmond")
        self.assertEqual(agent.phone, "9014131241")
        self.assertEqual(application.internal_referral, 'real-estate agent')

    def test_incomplete_referral_payload(self):
        random_objects.random_pricing(id='ffe6b1ec-cad1-430b-a58e-a341637a4780')

        convert_response_to_application(self.incomplete_referral_payload)

        updated_pricing = Pricing.objects.get(id='ffe6b1ec-cad1-430b-a58e-a341637a4780')
        agent = RealEstateAgent.objects.first()
        self.assertEqual(updated_pricing.agent, agent)

    @patch('utils.hubspot.requests')
    def test_get_lead_source_should_try_to_create_hubspot_contact_and_try_again(self, mock_requests):
        class MockResponse:
            __attrs__ = ['_content']

            def __init__(self, payload):
                self._content = payload

            @property
            def content(self):
                return self._content

            @property
            def status_code(self):
                return 204

        mock_requests.get.side_effect = [MockResponse(self.not_contact_payload), MockResponse(self.contact_payload)]
        get_lead_source_from_hubspot(uuid.uuid4(), '46f5b0be36ae6d90b5242941fca1a48c')

    def test_should_map_builder_referral_fields(self):
        convert_response_to_application(self.builder_referral_payload)
        convert_response_to_application(self.builder_referral_payload)

        customer = Customer.objects.get(email='brandon+2345675456787654567@homeward.com')
        application = Application.objects.get(customer=customer)
        builder = application.builder

        self.assertEqual(application.internal_referral, 'home builder')
        self.assertEqual(application.home_buying_stage, 'working with a builder')

        self.assertEqual(customer.name, 'Brandon Kirchner')
        self.assertEqual(customer.email, 'brandon+2345675456787654567@homeward.com')
        self.assertEqual(customer.phone, '1-098-765-4321')

        self.assertEqual(builder.company_name, 'MHI')
        self.assertEqual(builder.representative_name, 'Aidan Garza')
        self.assertEqual(builder.representative_email, 'aidan.garza@homeward.com')
        self.assertEqual(builder.representative_phone, '1-123-456-7890')

    def test_should_map_lender_referral_fields(self):
        convert_response_to_application(self.lender_referral_payload)
        convert_response_to_application(self.lender_referral_payload)

        customer = Customer.objects.get(email='brandon+tjwqoeritjdkfg@homeward.com')
        application = Application.objects.get(customer=customer)
        lender = application.mortgage_lender

        self.assertEqual(application.internal_referral, 'loan advisor')
        self.assertEqual(application.internal_referral_detail, 'fast track registration')

        self.assertEqual(lender.name, 'Aidan Garza')
        self.assertEqual(lender.email, 'aidan+mjgksrtgkj@homeward.com')

    def test_create_then_update(self):
        convert_response_to_application(self.create_payload)
        convert_response_to_application(self.first_update_payload)
        convert_response_to_application(self.second_update_payload)
        convert_response_to_application(self.third_update_payload)
        convert_response_to_application(self.fourth_update_payload)
        convert_response_to_application(self.fifth_update_payload)
        convert_response_to_application(self.sixth_update_payload)

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)
        agent = application.real_estate_agent
        lender = application.mortgage_lender
        current_home = application.current_home

        self.assertEqual(brandon.email, "brandon+testbug@homeward.com")
        self.assertEqual(brandon.phone, "1-234-523-4523")

        self.assertEqual(application.customer, brandon)
        self.assertEqual(application.home_buying_stage, 'viewing listings in person')
        self.assertEqual(application.stage, 'complete')
        self.assertEqual(application.min_price, 150000)
        self.assertEqual(application.max_price, 350000)
        self.assertEqual(application.move_in, "3-6 months")
        self.assertEqual(application.start_date.date(), datetime.date.today())
        self.assertEqual(application.lead_status, LeadStatus.NEW)
        self.assertEqual(application.self_reported_referral_source, "my_loan_officer")
        self.assertEqual(application.has_consented_to_receive_electronic_documents, True)

        self.assertEqual(agent.name, "brandon-agent kirchner-agent")
        self.assertEqual(agent.phone, "2345234523")
        self.assertEqual(agent.email, "brandon+agent@homeward.com")
        self.assertEqual(agent.company, "brandons real estate company")
        self.assertEqual(agent.self_reported_referral_source, "homeward certified training")
        self.assertEqual(agent.self_reported_referral_source_detail, "led by blake outlaw")

        self.assertEqual(lender.name, "brandon-lender kirchner-lender")
        self.assertEqual(lender.email, "brandon+lender@homeward.com")
        self.assertEqual(lender.phone, "1-234-523-4523")

        self.assertEqual(current_home.address.street, '1234 S Lamar Blvd')
        self.assertEqual(current_home.address.city, 'Austin')
        self.assertEqual(current_home.address.state, 'TX')
        self.assertEqual(current_home.address.zip, '78704')
        
        self.assertEqual(current_home.floors_count, 2)
        self.assertEqual(current_home.bedrooms_count, 3)
        self.assertEqual(current_home.home_size_sq_ft, 1234)
        self.assertEqual(current_home.master_on_main, True)

        self.assertEqual(current_home.kitchen_features, ["tile backsplash"])

    def test_existing_property_task_status_transitions(self):
        convert_response_to_application(self.create_payload)

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)

        address = Address.objects.create(street='1234 S Lamar Blvd', city='Austin', state='TX', zip='78704')
        application.current_home = CurrentHome.objects.create(address=address)

        run_task_operations(application)

        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.EXISTING_PROPERTY).status,
                         TaskProgress.NOT_STARTED.value)


        application.current_home.customer_value_opinion = '234523'
        application.current_home.save()
        run_task_operations(application)

        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.EXISTING_PROPERTY).status,
                         TaskProgress.COMPLETED.value)

    def test_photos_task_status_transitions(self):
        convert_response_to_application(self.create_payload)

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)

        self.assertEqual(application.stage, ApplicationStage.INCOMPLETE)

        address = Address.objects.create(street='1234 S Lamar Blvd', city='Austin', state='TX', zip='78704')
        home = CurrentHome.objects.create(address=address)
        application.current_home = home

        run_task_operations(application)
        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.PHOTO_UPLOAD).status,
                         TaskProgress.NOT_STARTED.value)

        CurrentHomeImage.objects.create(current_home=home, url='a')

        run_task_operations(application)
        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.PHOTO_UPLOAD).status,
                         TaskProgress.IN_PROGRESS.value)

        for n in range(5):
            CurrentHomeImage.objects.create(current_home=home, url=str(n))

        run_task_operations(application)
        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.PHOTO_UPLOAD).status,
                         TaskProgress.COMPLETED.value)
        for status in application.task_statuses.all():
            status.status = TaskProgress.COMPLETED
            status.save()
        application.save()

        self.assertEqual(application.stage, ApplicationStage.COMPLETE)

    def test_mortgage_task_depends_on_disclosures_task(self):
        convert_response_to_application(self.create_payload)

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)
        TaskStatus.objects.create(application=application,
                                  task_obj=Task.objects.get(name=TaskName.COLORADO_MORTGAGE),
                                  status=TaskProgress.IN_PROGRESS)
        task = TaskStatus.objects.create(application=application,
                                         task_obj=Task.objects.get(category=TaskCategory.DISCLOSURES),
                                         status=TaskProgress.IN_PROGRESS)

        self.assertEqual(application.task_statuses.get(task_obj__name=TaskName.COLORADO_MORTGAGE)
                         .is_actionable(), False)

        task.status = TaskProgress.COMPLETED
        task.save()

        self.assertEqual(application.task_statuses.get(task_obj__name=
                                                       TaskName.COLORADO_MORTGAGE).is_actionable(), True)

    def test_blend_status_updates_tasks_correctly(self):
        convert_response_to_application(self.create_payload)

        brandon = Customer.objects.get(name="Brandon Kirchner")
        application = Application.objects.get(customer=brandon)
        mortgage_task = TaskStatus.objects.create(application=application,
                                                  task_obj=Task.objects.get(name=TaskName.COLORADO_MORTGAGE),
                                                  status=TaskProgress.NOT_STARTED)
        disclosure_task = TaskStatus.objects.create(application=application,
                                                    task_obj=Task.objects.get(category=TaskCategory.DISCLOSURES),
                                                    status=TaskProgress.IN_PROGRESS)

        disclosure_task.status = TaskProgress.COMPLETED
        disclosure_task.save()

        run_task_operations(application)

        self.assertEqual(mortgage_task.status, TaskProgress.NOT_STARTED)

        application.blend_status = BlendStatus.APPLICATION_CREATED
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.IN_PROGRESS)

        application.blend_status = BlendStatus.APPLICATION_ARCHIVED
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.IN_PROGRESS)

        application.blend_status = 'Application in progress: Getting Started'
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.IN_PROGRESS)

        application.blend_status = 'Application completed (Borrower Submit)'
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.UNDER_REVIEW)

        application.blend_status = 'poop'
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.UNDER_REVIEW)

        application.blend_status = 'Application completed (Borrower Submit)'
        application.stage = ApplicationStage.APPROVED
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.COMPLETED)

        application.stage = ApplicationStage.OPTION_PERIOD
        application.save()
        run_task_operations(application)

        self.assertEqual(TaskStatus.objects.get(id=mortgage_task.id).status, TaskProgress.COMPLETED)

    @patch('utils.mailer.send_hca_referral_sign_up_notification')
    def test_certified_agent(self, mailer_patch):
        agent = RealEstateAgent.objects.create(id='01a582d6-8f1c-4474-b4d1-05a340362d76', name='brandon kirchner',
                                               phone='1-234-5678', email='brandon@homeward.com',
                                               company='brandons brokerage', is_certified=True, sf_id='blah')

        convert_response_to_application(self.certified_agent_create)

        application = Application.objects.get(customer__email='brandon+testbug@homeward.com')
        
        mailer_patch.assert_called_once_with(ANY, application.customer.name, application.customer.get_first_name())
        mailer_patch.reset_mock()

        self.assertEquals(agent.id, str(application.listing_agent.id))
        self.assertEquals(agent.id, str(application.buying_agent.id))
        self.assertEquals(application.internal_referral, 'real-estate agent')
        self.assertEquals(application.internal_referral_detail, 'referral link')

        # test updates as well
        convert_response_to_application(self.certified_agent_create)
        
        mailer_patch.assert_not_called()

        application = Application.objects.get(customer__email='brandon+testbug@homeward.com')

        self.assertEquals(agent.id, str(application.listing_agent.id))
        self.assertEquals(agent.id, str(application.buying_agent.id))
        self.assertEquals(application.internal_referral, 'real-estate agent')
        self.assertEquals(application.internal_referral_detail, 'referral link')

    def test_non_certified_agent(self):
        agent = RealEstateAgent.objects.create(id='01a582d6-8f1c-4474-b4d1-05a340362d76', name='brandon kirchner',
                                               phone='1-234-5678', email='brandon@homeward.com',
                                               company='brandons brokerage')

        convert_response_to_application(self.regular_agent_create)

        application = Application.objects.get(customer__email='brandon+testbug@homeward.com')

        self.assertEquals(agent.id, str(application.listing_agent.id))
        self.assertEquals(agent.id, str(application.buying_agent.id))
        self.assertEquals(application.internal_referral, 'real-estate agent')
        self.assertEquals(application.internal_referral_detail, 'registered client')

        # test updates as well
        convert_response_to_application(self.regular_agent_create)

        application = Application.objects.get(customer__email='brandon+testbug@homeward.com')

        self.assertEquals(agent.id, str(application.listing_agent.id))
        self.assertEquals(agent.id, str(application.buying_agent.id))
        self.assertEquals(application.internal_referral, 'real-estate agent')
        self.assertEquals(application.internal_referral_detail, 'registered client')

    def test_buy_only_payload(self):
        convert_response_to_application(self.buy_only_payload)
        app = Application.objects.get(customer__email='user@email.com')

        self.assertEquals(app.product_offering, ProductOffering.BUY_ONLY.value)

    def test_buy_only_payload_doesnt_change_product_offering_on_updates(self):
        """
        on application creation, we set the product offering based on the do_you_have_a_home_to_sell slug.
        If they initially answer "No", when in reality the answer is yes, we change the application directly,
        but the payload from questionnaire-service remains unchanged, so we need to ensure updates don't set
        product offering, and that current home changes are propagated correctly.
        """

        convert_response_to_application(self.buy_only_payload)
        app = Application.objects.get(customer__email='user@email.com')

        self.assertEquals(app.product_offering, ProductOffering.BUY_ONLY.value)
        self.assertIsNone(app.current_home)

        app.product_offering = ProductOffering.BUY_SELL
        app.current_home = random_objects.random_current_home()
        app.save()

        convert_response_to_application(self.buy_only_payload)
        app.refresh_from_db()
        self.assertEquals(app.product_offering, ProductOffering.BUY_SELL.value)
        self.assertEquals(app.current_home.full_bathrooms_count, 2)
    
    def test_sets_shopping_location_when_city_looking_in_answered(self): 
        convert_response_to_application(self.researching_online_application_payload)

        application = Application.objects.get(customer__email='regina.deangelis+researchonlinetest@homeward.com')
        self.assertEqual(application.shopping_location, 'Austin, TX, USA')
    
    def test_sets_shopping_location_when_viewing_listings_online(self): 
        convert_response_to_application(self.viewing_listings_payload)
        application = Application.objects.get(customer__email='regina.deangelis+denverlistingsinperson@homeward.com') 
        self.assertEqual(application.shopping_location, 'Denver, CO, USA')
    
    def test_sets_shopping_location_when_making_an_offer(self):
        convert_response_to_application(self.making_an_offer_payload)
        application = Application.objects.get(customer__email='regina.deangelis+makingoffertest@homeward.com')
        self.assertEqual(application.shopping_location, 'Austin, TX, USA')
    
    def test_sets_shopping_location_when_under_contract(self):
        convert_response_to_application(self.under_contract_payload)
        application = Application.objects.get(customer__email='regina.deangelis+makinganoffer@gmail.com')
        self.assertEqual(application.shopping_location, 'Sunset Valley, TX, USA')
    

    def test_when_tasks_are_completed_bwc_app_stage_moves_to_complete(self): 
        convert_response_to_application(self.viewing_listings_payload)
        application = Application.objects.get(customer__email='regina.deangelis+denverlistingsinperson@homeward.com') 
        application_tasks = TaskStatus.objects.filter(application=application)
        self.assertEqual(application.stage, 'incomplete')
        task_stats = application_tasks.values_list('status', flat=True)
        self.assertEqual('Not started' in task_stats, True)
        
        for task in application_tasks:
            task.status = 'Completed'
            task.save()

        application.refresh_from_db()
        self.assertEqual(application.stage, 'complete')

    def test_when_tasks_are_completed_bbys_app_stage_moves_to_complete(self): 
        convert_response_to_application(self.viewing_listings_payload)
        application = Application.objects.get(customer__email='regina.deangelis+denverlistingsinperson@homeward.com') 
        application.product_offering = 'buy-sell'
        application.save()
        application_tasks = TaskStatus.objects.filter(application=application)
        self.assertEqual(application.stage, 'incomplete')
        task_stats = application_tasks.values_list('status', flat=True)
        self.assertEqual('Not started' in task_stats, True)
        
        for task in application_tasks:
            task.status = 'Completed'
            task.save()

        application.refresh_from_db()
        self.assertEqual(application.stage, 'complete')