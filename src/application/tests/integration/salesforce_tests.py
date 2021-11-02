import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from rest_framework.test import APITestCase

from application.models.acknowledgement import Acknowledgement
from application.models.address import Address
from application.models.application import Application
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.disclosure import Disclosure
from application.models.loan import Loan
from application.models.real_estate_agent import AgentType, RealEstateAgent
from application.models.real_estate_lead import RealEstateLead
from application.models.offer import Offer
from application.tests import random_objects
from blend.models import Followup
from user.models import User
from utils.salesforce import update_or_create_loan_from_salesforce


class SalesforceTests(APITestCase):
    module_dir = str(Path(__file__).parent)
    fixtures = [os.path.join(module_dir, "../static/filled_app_salesforce_test.json")]

    def setUp(self):
        self.app = Application.objects.get(pk="aca30e9e-776b-44fb-ba37-93e4b195cefe")
        self.user = User.objects.get(pk=1)

    def test_should_transform_application(self):
        sf_payload = self.app.to_salesforce_representation()
        self.assertEqual(len(sf_payload), 58)
        self.assertEqual(sf_payload.get(Application.WORKING_WITH_AN_AGENT_FIELD), "yes")
        self.assertEqual(sf_payload.get(Application.HOME_TO_SELL_FIELD), "yes")
        self.assertEqual(sf_payload.get(Application.WORKING_WITH_A_LENDER_FIELD), "yes")
        self.assertEquals(sf_payload.get(RealEstateAgent.BUYING_AGENT_ID_FIELD), self.app.buying_agent.sf_id)
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_ID_FIELD), self.app.listing_agent.sf_id)
        self.assertEqual(sf_payload.get(Customer.EMAIL_FIELD), self.app.customer.email),
        self.assertEqual(sf_payload.get(Customer.PHONE_FIELD), self.app.customer.phone),
        self.assertEqual(sf_payload.get(Customer.FIRST_NAME_FIELD), self.app.customer.get_first_name()),
        self.assertEqual(sf_payload.get(Customer.LAST_NAME_FIELD), self.app.customer.get_last_name())
        self.assertEqual(sf_payload.get(Application.CUSTOMER_ID_FIELD), str(self.app.customer.id)),
        self.assertEqual(sf_payload.get(Application.PRODUCT_OFFERING_FIELD), self.app.product_offering),
        self.assertEqual(sf_payload.get(Application.NEEDS_LISTING_AGENT_FIELD), self.app.needs_listing_agent),
        self.assertEqual(sf_payload.get(Application.NEEDS_BUYING_AGENT_FIELD), self.app.needs_buying_agent)
        self.assertEqual(sf_payload.get(Application.AGENT_CLIENT_CONTACT_PREFERENCE), self.app.agent_client_contact_preference)
        self.assertEqual(sf_payload.get(Application.SALESFORCE_COMPANY_ID_FIELD), self.app.salesforce_company_id)

    def test_should_transform_real_estate_lead(self):
        lead = RealEstateLead.objects.get(pk="05096c81-5f4e-4e1e-8f2b-69e49e2ebc3a")
        sf_payload = lead.to_salesforce_representation()
        self.assertEqual(sf_payload.get(RealEstateLead.NEEDS_BUYING_AGENT_FIELD), lead.needs_buying_agent)
        self.assertEqual(sf_payload.get(RealEstateLead.NEEDS_LISTING_AGENT_FIELD), lead.needs_listing_agent)
        self.assertEqual(sf_payload.get(RealEstateLead.CUSTOMER_REPORTED_STAGE_FIELD), lead.home_buying_stage)
        self.assertEqual(sf_payload.get(Application.RECORD_TYPE_ID_FIELD), Application.RECORD_TYPE_ID_VALUE)
        self.assertEqual(sf_payload.get(Customer.FIRST_NAME_FIELD), lead.customer.get_first_name())
        self.assertEqual(sf_payload.get(Customer.LAST_NAME_FIELD), lead.customer.get_last_name())
        self.assertEqual(sf_payload.get(Customer.PHONE_FIELD), lead.customer.phone)
        self.assertEqual(sf_payload.get(Customer.EMAIL_FIELD), lead.customer.email)
        self.assertEqual(sf_payload.get(Address.BILLING_STREET_FIELD), lead.address.street)
        self.assertEqual(sf_payload.get(Address.BILLING_CITY_FIELD), lead.address.city)
        self.assertEqual(sf_payload.get(Address.BILLING_STATE_FIELD), lead.address.state)
        self.assertEqual(sf_payload.get(Address.BILLING_POSTAL_CODE_FIELD), lead.address.zip)

    def test_should_transform_real_estate_agent(self):
        agent = self.app.listing_agent
        sf_payload = agent.to_salesforce_representation(AgentType.LISTING)
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_FIRST_NAME_FIELD), agent.get_first_name())
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_LAST_NAME_FIELD), agent.get_last_name())
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_PHONE_FIELD), agent.phone)
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_EMAIL_FIELD), agent.email)
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_COMPANY_FIELD), agent.company)
        self.assertEqual(sf_payload.get(RealEstateAgent.LISTING_AGENT_ID_FIELD), agent.sf_id)

        agent = self.app.buying_agent
        sf_payload = agent.to_salesforce_representation(AgentType.BUYING)
        self.assertEqual(sf_payload.get(RealEstateAgent.BUYING_AGENT_FIRST_NAME_FIELD), agent.get_first_name())
        self.assertEqual(sf_payload.get(RealEstateAgent.BUYING_AGENT_LAST_NAME_FIELD), agent.get_last_name())
        self.assertEqual(sf_payload.get(RealEstateAgent.BUYING_AGENT_PHONE_FIELD), agent.phone)
        self.assertEqual(sf_payload.get(RealEstateAgent.BUYING_AGENT_EMAIL_FIELD), agent.email)
        self.assertEqual(sf_payload.get(RealEstateAgent.BUYING_AGENT_COMPANY_FIELD), agent.company)
        self.assertEqual(sf_payload.get(RealEstateAgent.BUYING_AGENT_ID_FIELD), agent.sf_id)

    def test_should_transform_current_home(self):
        current_home = self.app.current_home
        payload = current_home.to_salesforce_representation()

        self.assertEqual(payload.get(CurrentHome.OLD_HOME_CUSTOMER_HOME_VALUE_OPINION_FIELD), str(current_home.customer_value_opinion))
        self.assertEqual(payload.get(CurrentHome.LISTING_STATUS_FIELD), str(current_home.listing_status))
        self.assertEqual(payload.get(CurrentHome.LISTING_URL_FIELD), str(current_home.listing_url))
        self.assertEqual(payload.get(CurrentHome.SELLER_CONCESSIONS_FIELD), str(current_home.total_concession_amount))
        self.assertEqual(payload.get(CurrentHome.OPTION_PERIOD_EXPIRATION_DATE_FIELD), str(current_home.option_period_expiration_date.date()))
        self.assertEqual(payload.get(CurrentHome.CLOSING_DATE_FIELD), str(current_home.closing_date.date()))
        self.assertEqual(payload.get(CurrentHome.HAS_BASEMENT_FIELD), current_home.has_basement)
        self.assertEqual(payload.get(CurrentHome.BASEMENT_FINISHED_OR_UNFINISHED), str(current_home.basement_type))
        self.assertEqual(payload.get(CurrentHome.BASEMENT_SQ_FT_FIELD), str(current_home.basement_size_sq_ft))
        self.assertEqual(payload.get(CurrentHome.DO_YOU_HAVE_A_VIEW_FIELD), str(current_home.property_view_type))
        self.assertEqual(payload.get(CurrentHome.ADDITIONAL_CUSTOMER_NOTES_FIELD), str(current_home.customer_notes))
        self.assertEqual(payload.get(CurrentHome.NUMBER_OF_STORIES_FIELD), str(current_home.floors_count))
        self.assertEqual(payload.get(CurrentHome.BEDROOMS_COUNT_FIELD), str(current_home.bedrooms_count))
        self.assertEqual(payload.get(CurrentHome.SQUARE_FOOTAGE_FIELD), str(current_home.home_size_sq_ft))
        self.assertEqual(payload.get(CurrentHome.MASTER_ON_MAIN_FIELD), current_home.master_on_main)
        self.assertEqual(payload.get(CurrentHome.FULL_BATH_COUNT_FIELD), str(current_home.full_bathrooms_count))
        self.assertEqual(payload.get(CurrentHome.PARTIAL_BATH_COUNT_FIELD), str(current_home.partial_bathrooms_count))
        self.assertEqual(payload.get(CurrentHome.KITCHEN_APPLIANCES_TYPE_FIELD), str(current_home.kitchen_appliance_type))
        self.assertEqual(payload.get(CurrentHome.KITCHEN_FEATURES_FIELD), str(current_home.kitchen_features))
        self.assertEqual(payload.get(CurrentHome.COUNTERS_TYPES_FIELD), str(current_home.kitchen_countertop_type))
        self.assertEqual(payload.get(CurrentHome.MASTER_BATH_CONDITION_FIELD), str(current_home.master_bathroom_condition))
        self.assertEqual(payload.get(CurrentHome.KITCHEN_REMODEL_FIELD), str(current_home.kitchen_has_been_remodeled))
        self.assertEqual(payload.get(CurrentHome.INTERIOR_WALL_CONDITION_FIELD), str(current_home.interior_walls_condition))
        self.assertEqual(payload.get(CurrentHome.FLOORING_TYPE_FIELD), str(current_home.flooring_types))
        self.assertEqual(payload.get(CurrentHome.GARAGE_SPACES_COUNT_FIELD), str(current_home.garage_spaces_count))
        self.assertEqual(payload.get(CurrentHome.ROOF_AGE_FIELD), str(current_home.roof_age_range))
        self.assertEqual(payload.get(CurrentHome.EXTERIOR_WALLS_TYPE_FIELD), str(current_home.exterior_walls_types))
        self.assertEqual(payload.get(CurrentHome.OTHER_HOME_SITUATIONS_FIELD), str(current_home.home_features))
        self.assertEqual(payload.get(CurrentHome.HVAC_AGE_FIELD), str(current_home.hvac_age_range))
        self.assertEqual(payload.get(CurrentHome.FLOODZONE_FIELD), str(current_home.in_floodzone))
        self.assertEqual(payload.get(CurrentHome.ADDTIONS_MADE_FIELD), current_home.has_made_addition)
        self.assertEqual(payload.get(CurrentHome.ADDITION_SIZE_FIELD), str(current_home.addition_size_sq_ft))
        self.assertEqual(payload.get(CurrentHome.ADDITION_TYPE_FIELD), str(current_home.addition_type))
        self.assertEqual(payload.get(CurrentHome.CARPET_CONDITON_FIELD), str(current_home.carpet_flooring_condition))
        self.assertEqual(payload.get(CurrentHome.HARDWOOD_CONDITION_FIELD), str(current_home.hardwood_flooring_condition))
        self.assertEqual(payload.get(CurrentHome.POOL_FIELD), str(current_home.pool_type))
        self.assertEqual(payload.get(CurrentHome.BACK_YARD_CONDITION_FIELD), str(current_home.back_yard_condition))
        self.assertEqual(payload.get(CurrentHome.FRONT_YARD_CONDITION_FIELD), str(current_home.front_yard_condition))
        self.assertEqual(payload.get(CurrentHome.SIDES_WITH_MASONARY_FIELD), str(current_home.sides_with_masonry_count))
        self.assertEqual(payload.get(CurrentHome.REPAIR_OR_UPDATE_DETAIL_FIELD), str(current_home.repair_or_update_detail))        
        self.assertEqual(payload.get(Address.GENERAL_ADDRESS_CITY_FIELD), str(current_home.address.city))        
        self.assertEqual(payload.get(Address.GENERAL_ADDRESS_STREET_FIELD), str(current_home.address.street))        
        self.assertEqual(payload.get(Address.GENERAL_ADDRESS_UNIT_FIELD), str(current_home.address.unit))        
        self.assertEqual(payload.get(Address.GENERAL_ADDRESS_STATE_FIELD), str(current_home.address.state))        
        self.assertEqual(payload.get(Address.GENERAL_ADDRESS_ZIP_FIELD), str(current_home.address.zip))        
        self.assertEqual(payload.get(CurrentHome.NAME), str(current_home.address.get_inline_address()))

    def test_should_not_add_agents_if_not_present(self):
        self.app.listing_agent = None
        self.app.buying_agent = None
        self.app.save()
        payload = self.app.to_salesforce_representation()
        self.assertIsNone(payload.get(RealEstateAgent.LISTING_AGENT_FIRST_NAME_FIELD))
        self.assertIsNone(payload.get(RealEstateAgent.BUYING_AGENT_FIRST_NAME_FIELD))

    def test_should_not_generate_first_or_last_login_when_no_user(self):
        self.user.email = "Someemail@gmail.com"
        self.user.save()
        payload = self.app.to_salesforce_representation()
        self.assertEqual(payload.get(User.FIRST_APPLICATION_LOGIN_FIELD), None)
        self.assertEqual(payload.get(User.LAST_APPLICATION_LOGIN_FIELD), None)

    def test_should_map_just_first_login_if_last_is_none(self):
        self.user.date_joined = datetime.today()
        self.user.email = "brandon@homeward.com"
        self.user.last_login = None
        self.user.save()

        payload = self.app.to_salesforce_representation()

        self.assertEqual(payload.get(User.FIRST_APPLICATION_LOGIN_FIELD), self.user.date_joined.strftime("%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(payload.get(User.LAST_APPLICATION_LOGIN_FIELD), None)

    def test_should_map_both_first_and_last(self):
        self.user.date_joined = datetime.now()
        self.user.last_login = datetime.now()
        self.user.save()

        payload = self.app.to_salesforce_representation()

        self.assertEqual(payload.get(User.FIRST_APPLICATION_LOGIN_FIELD), self.user.date_joined.strftime("%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(payload.get(User.LAST_APPLICATION_LOGIN_FIELD), self.user.last_login.strftime("%Y-%m-%dT%H:%M:%S"))

    def test_should_transform_offer(self):
        application = random_objects.random_application()
        offer = random_objects.random_offer(application=application)
        payload = offer.to_salesforce_representation()

        self.assertEqual(payload.get(Offer.YEAR_BUILT_FIELD), offer.year_built)
        self.assertEqual(payload.get(Offer.HOME_SQUARE_FOOTAGE_FIELD), offer.home_square_footage)
        self.assertEqual(payload.get(Offer.PROPERTY_TYPE_FIELD), offer.property_type)
        self.assertEqual(payload.get(Offer.LESS_THAN_ONE_ACRE_FIELD), 'Yes' if offer.less_than_one_acre else 'No')
        self.assertEqual(payload.get(Offer.HOME_LIST_PRICE_FIELD), offer.home_list_price)
        self.assertEqual(payload.get(Offer.OFFER_PRICE_FIELD), offer.offer_price)
        self.assertEqual(payload.get(Offer.CONTRACT_TYPE_FIELD), offer.contract_type)
        self.assertEqual(payload.get(Offer.OTHER_OFFER_FIELD), offer.other_offers)
        self.assertEqual(payload.get(Offer.OFFER_DEADLINE_FIELD), offer.offer_deadline)
        self.assertEqual(payload.get(Offer.LEASE_BACK_TO_SELLER_FIELD), offer.plan_to_lease_back_to_seller)
        self.assertEqual(payload.get(Offer.WAIVE_APPRAISAL_FIELD), offer.waive_appraisal)
        self.assertEqual(payload.get(Offer.ADDRESS_STREET_FIELD), offer.offer_property_address.street)
        self.assertEqual(payload.get(Offer.ADDRESS_CITY_FIELD), offer.offer_property_address.city)
        self.assertEqual(payload.get(Offer.ADDRESS_STATE_FIELD), offer.offer_property_address.state)
        self.assertEqual(payload.get(Offer.ADDRESS_ZIP_FIELD), offer.offer_property_address.zip)
    
    def test_should_transform_blend_followup(self):
        application = random_objects.random_application(stage="complete")
        loan = random_objects.random_loan(application=application, salesforce_id='1111111' )
        followup = random_objects.random_followup(application=application, loan=loan, blend_application_id='111111111', blend_followup_id='7254aeb7-898b-4aae-bfbc-df86dc861635')
        payload = followup.to_salesforce_representation()

        self.assertEqual(payload.get(Followup.TYPE), followup.followup_type)
        self.assertEqual(payload.get(Followup.STATUS), followup.status)
        self.assertEqual(payload.get(Followup.DESCRIPTION), followup.description)
        self.assertEqual(payload.get(Followup.REQUESTED_DATE), followup.requested_date.strftime("%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(payload.get(Followup.LOAN_APPLICATION_ID), followup.loan.salesforce_id)
        self.assertEqual(payload.get(Followup.BLEND_APPLICATION_ID), followup.blend_application_id)
        self.assertEqual(payload.get(Followup.BLEND_FOLLOWUP_ID), followup.blend_followup_id)

    def test_should_include_new_service_agreement_acknowledged_date(self):
        disclosure = Disclosure.objects.create(name='service agreement (tx - buy-sell) v4',
                                               disclosure_type='service_agreement',
                                               document_url='www.blah.com',
                                               buying_state='tx',
                                               active=True)
        acknowledgement = Acknowledgement.objects.create(application=self.app, disclosure=disclosure)
        acknowledgement.is_acknowledged = True
        acknowledgement.save()

        sf_payload = self.app.to_salesforce_representation()
        self.assertIsNotNone(sf_payload.get(Application.NEW_SERVICE_AGREEMENT_ACKNOWLEDGED_DATE))
        self.assertEqual(sf_payload.get(Application.NEW_SERVICE_AGREEMENT_ACKNOWLEDGED_DATE)[:10],
                         self.app.new_service_agreement_acknowledged_date.strftime('%Y-%m-%d'))

    def test_transforming_salesforce_payload_to_loan(self):
        app = random_objects.random_application(new_salesforce='test-sf-id')
        salesforce_payload = {
            Loan.CUSTOMER_FIELD: app.new_salesforce,
            Loan.BLEND_APPLICATION_ID_FIELD: 'test-blend-id',
            Loan.LOAN_STATUS_FIELD: "Application in progress: Getting Started",
            Loan.SALESFORCE_ID_FIELD: 'test-id',
            Loan.DENIAL_REASON_FIELD: 'Not enough money',
            Loan.BASE_CONVENIENCE_FEE_FIELD: 1.9,
            Loan.ESTIMATED_BROKER_CONVENIENCE_FEE_CREDIT_FIELD: 4120.0,
            Loan.ESTIMATED_MORTGAGE_CONVENIENCE_FEE_CREDIT_FIELD: 51140.0,
            Loan.ESTIMATED_DAILY_RENT: 81.73,
            Loan.ESTIMATED_MONTHLY_RENT: 4027.34,
            Loan.ESTIMATED_EARNEST_DEPOSIT_PERCENTAGE: 2,
        }

        update_or_create_loan_from_salesforce(app, salesforce_payload)

        self.assertEqual(app.loans.first().status, "Application in progress: Getting Started")
        self.assertEqual(app.loans.first().salesforce_id, "test-id")
        self.assertEqual(app.loans.first().blend_application_id, "test-blend-id")
        self.assertEqual(app.loans.first().denial_reason, "Not enough money")
        self.assertAlmostEqual(app.loans.first().base_convenience_fee, Decimal(1.9))
        self.assertAlmostEqual(app.loans.first().estimated_broker_convenience_fee_credit, Decimal(4120.0))
        self.assertAlmostEqual(app.loans.first().estimated_mortgage_convenience_fee_credit, Decimal(51140.0))
        self.assertAlmostEqual(app.loans.first().estimated_daily_rent, Decimal(81.73))
        self.assertAlmostEqual(app.loans.first().estimated_monthly_rent, Decimal(4027.34))
        self.assertAlmostEqual(app.loans.first().estimated_earnest_deposit_percentage, Decimal(2))
