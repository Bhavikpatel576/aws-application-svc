from datetime import datetime, date
from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from faker import Faker
from pytz import UTC

from application import constants
from application.models.application import Application
from application.models.internal_support_user import InternalSupportUser
from application.models.loan import Loan
from application.models.new_home_purchase import NewHomePurchase
from application.models.offer import Offer, PropertyType, ContractType, OtherOffers, PlanToLeaseBackToSeller, \
    WaiveAppraisal
from application.models.real_estate_agent import RealEstateAgent
from application.models.rent import Rent
from application.tests import random_objects
from utils import salesforce

fake = Faker()


class SalesforceTests(TestCase):
    def setUp(self):
        self.application = random_objects.random_application()
        self.listing_agent = self.application.listing_agent
        self.buying_agent = self.application.buying_agent
        self.fake_agent_id = str(fake.md5())
        self.new_home_purchase = random_objects.random_new_home_purchase()
        self.assertEqual(RealEstateAgent.objects.all().count(), 2)

    def test_failure_no_customer_in_payload_for_sync_loan_record_from_salesforce(self):
        with self.assertRaises(KeyError):
            sf_loan_trigger_payload = {
                Loan.SALESFORCE_ID_FIELD: "test12345",
                Loan.BLEND_APPLICATION_ID_FIELD: "69af5d15-22a4-4052-96d3-c526339532e9",
                Loan.LOAN_STATUS_FIELD: "Application in progress: Getting Started",
            }
            salesforce.sync_loan_record_from_salesforce(sf_loan_trigger_payload)

    def test_failure_no_email_found_in_db_for_sync_loan_record_from_salesforce(self):
        with self.assertRaises(ObjectDoesNotExist):
            sf_loan_trigger_payload = {
                Loan.CUSTOMER_FIELD: "test54321",
                Loan.SALESFORCE_ID_FIELD: "test12345",
                Loan.BLEND_APPLICATION_ID_FIELD: "69af5d15-22a4-4052-96d3-c526339532e9",
                Loan.LOAN_STATUS_FIELD: "Application in progress: Getting Started",
            }
            salesforce.sync_loan_record_from_salesforce(sf_loan_trigger_payload)

    def test_failure_none_set_for_customer_in_payload_for_sync_loan_record_from_salesforce(self):
        with self.assertRaises(ValueError):
            sf_loan_trigger_payload = {
                Loan.CUSTOMER_FIELD: None,
                Loan.SALESFORCE_ID_FIELD: "test12345",
                Loan.BLEND_APPLICATION_ID_FIELD: "69af5d15-22a4-4052-96d3-c526339532e9",
                Loan.LOAN_STATUS_FIELD: "Application in progress: Getting Started",
            }
            salesforce.sync_loan_record_from_salesforce(sf_loan_trigger_payload)

    def test_update_or_create_loan_from_salesforce(self):
        # create first Loan record
        sf_loan_trigger_payload = {
            Loan.SALESFORCE_ID_FIELD: "test1",
            Loan.BLEND_APPLICATION_ID_FIELD: "69af5d15-22a4-4052-96d3-c526339532e9",
            Loan.LOAN_STATUS_FIELD: "Application in progress: Getting Started",
        }
        salesforce.update_or_create_loan_from_salesforce(self.application, sf_loan_trigger_payload)
        self.assertEqual(Loan.objects.all().count(), 1)
        loan = Loan.objects.first()
        self.assertEqual(loan.status, "Application in progress: Getting Started")
        self.assertEqual(loan.blend_application_id, "69af5d15-22a4-4052-96d3-c526339532e9")
        self.assertEqual(loan.salesforce_id, "test1")
        self.assertIsNone(loan.denial_reason, "Denial Reason should be Null")
        self.assertEqual(loan.application_id, self.application.id)

        # create a second record
        sf_loan_trigger_payload = {
            Loan.SALESFORCE_ID_FIELD: "test2",
            Loan.BLEND_APPLICATION_ID_FIELD: "00af5d15-22a4-4052-96d3-c52633950000",
            Loan.LOAN_STATUS_FIELD: "Application in progress: Getting Started",
        }
        salesforce.update_or_create_loan_from_salesforce(self.application, sf_loan_trigger_payload)
        self.assertEqual(Loan.objects.all().count(), 2)

        # Verify update works by checking loan status was updated
        sf_loan_trigger_payload = {
            Loan.SALESFORCE_ID_FIELD: "test1",
            Loan.BLEND_APPLICATION_ID_FIELD: "69af5d15-22a4-4052-96d3-c526339532e9",
            Loan.LOAN_STATUS_FIELD: "Application created",
            Loan.DENIAL_REASON_FIELD: "Credit Score does not meet requirement",
        }
        salesforce.update_or_create_loan_from_salesforce(self.application, sf_loan_trigger_payload)
        self.assertEqual(Loan.objects.all().count(), 2)
        loan = Loan.objects.get(blend_application_id="69af5d15-22a4-4052-96d3-c526339532e9")
        self.assertEqual(loan.status, "Application created")
        self.assertEqual(loan.blend_application_id, "69af5d15-22a4-4052-96d3-c526339532e9")
        self.assertEqual(loan.salesforce_id, "test1")
        self.assertEqual(loan.denial_reason, "Credit Score does not meet requirement")
        self.assertEqual(loan.application_id, self.application.id)

        # verify only loan 1 was updated
        loan2 = Loan.objects.get(blend_application_id="00af5d15-22a4-4052-96d3-c52633950000")
        self.assertIsNone(loan2.denial_reason, "Denial Reason should be Null")
        self.assertEqual(loan2.status, "Application in progress: Getting Started")

    def test_update_real_estate_agent(self):
        with patch.object(salesforce.Salesforce, 'get_account_by_id') as mock_get_account_by_id:
            mock_data = {
                RealEstateAgent.LISTING_AGENT_FIRST_NAME_FIELD: fake.first_name(),
                RealEstateAgent.LISTING_AGENT_LAST_NAME_FIELD: fake.last_name(),
                RealEstateAgent.LISTING_AGENT_PHONE_FIELD: fake.phone_number(),
                RealEstateAgent.LISTING_AGENT_EMAIL_FIELD: fake.email(),
                RealEstateAgent.LISTING_AGENT_COMPANY_FIELD: fake.company(),
            }
            mock_get_account_by_id.return_value = mock_data

            application_stub = {
                RealEstateAgent.LISTING_AGENT_ID_FIELD: self.fake_agent_id,
                RealEstateAgent.BUYING_AGENT_ID_FIELD: self.fake_agent_id,
            }

            salesforce.update_real_estate_agent(self.application, application_stub)
            # It should create a new real estate agent
            self.assertEqual(RealEstateAgent.objects.all().count(), 3)
            # It should not update the existing agent objects
            self.assertNotEqual(self.listing_agent, self.application.listing_agent)
            self.assertNotEqual(self.buying_agent, self.application.buying_agent)
            # It should update the application's listing_agent and buying_agents
            self.assertEqual(self.application.listing_agent, self.application.buying_agent)
            self.assertEqual(self.application.listing_agent.sf_id, self.fake_agent_id)

    def test_update_cx_manager(self):
        with patch.object(salesforce.Salesforce, 'get_user_by_id') as mock_get_user_by_id:
            mock_data = {
                InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
                InternalSupportUser.USER_BIO: "Some BIO...",
                InternalSupportUser.USER_FIRST_NAME: "Test",
                InternalSupportUser.USER_LAST_NAME: "CX",
                InternalSupportUser.USER_PHONE: "1111111111",
                InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PROFILE_NAME: "CXA",
                InternalSupportUser.ID_FIELD: "test12345"
            }
            mock_get_user_by_id.return_value = mock_data
            sf_account_trigger_payload = {
                InternalSupportUser.OWNER_ID_FIELD: "test12345"
            }

            salesforce.update_cx_manager(self.application, sf_account_trigger_payload)
            # It should create a new cx manager
            self.assertEqual(InternalSupportUser.objects.all().count(), 1)

            # It should update an existing cx manager
        with patch.object(salesforce.Salesforce, 'get_user_by_id') as mock_get_user_by_id:
            mock_data = {
                InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
                InternalSupportUser.USER_BIO: "Some BIO...",
                InternalSupportUser.USER_FIRST_NAME: "Test",
                InternalSupportUser.USER_LAST_NAME: "CX",
                InternalSupportUser.USER_PHONE: "2222222222",
                InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PROFILE_NAME: "CXA",
                InternalSupportUser.ID_FIELD: "test12345"
            }
            mock_get_user_by_id.return_value = mock_data
            sf_account_trigger_payload = {
                InternalSupportUser.OWNER_ID_FIELD: "test12345",
                InternalSupportUser.USER_PHONE: "2222222222"
            }
            salesforce.update_cx_manager(self.application, sf_account_trigger_payload)
            cx_manager = InternalSupportUser.objects.get(email="test.cx@homeward.com")
            self.assertEqual(InternalSupportUser.objects.first().phone, "2222222222")
            self.assertEqual(self.application.cx_manager, cx_manager)
            self.assertIsNone(self.application.loan_advisor)

    def test_update_approval_specialist_on_application(self):
        existing_isu = InternalSupportUser.objects.create(sf_id='test12345')

        with patch.object(salesforce.Salesforce, 'get_user_by_id') as mock_get_user_by_id:
            mock_data = {
                InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
                InternalSupportUser.USER_BIO: "Some BIO...",
                InternalSupportUser.USER_FIRST_NAME: "Test",
                InternalSupportUser.USER_LAST_NAME: "CX",
                InternalSupportUser.USER_PHONE: "2222222222",
                InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PROFILE_NAME: "CXA",
                InternalSupportUser.ID_FIELD: "test12345"
            }
            mock_get_user_by_id.return_value = mock_data
            salesforce_data = {
                Application.APPROVAL_SPECIALIST: 'test12345'
            }

            salesforce.update_approval_specialist_on_application(application=self.application,
                                                                 salesforce_data=salesforce_data)
            self.assertIsNotNone(self.application.approval_specialist)
            self.assertEqual(self.application.approval_specialist.sf_id, 'test12345')
            self.assertEqual(self.application.approval_specialist, existing_isu)

    def test_create_approval_specialist_on_application(self):
        with patch.object(salesforce.Salesforce, 'get_user_by_id') as mock_get_user_by_id:
            mock_data = {
                InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
                InternalSupportUser.USER_BIO: "Some BIO...",
                InternalSupportUser.USER_FIRST_NAME: "Test",
                InternalSupportUser.USER_LAST_NAME: "CX",
                InternalSupportUser.USER_PHONE: "2222222222",
                InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PROFILE_NAME: "CXA",
                InternalSupportUser.ID_FIELD: "test12345"
            }
            mock_get_user_by_id.return_value = mock_data
            salesforce_data = {
                Application.APPROVAL_SPECIALIST: 'test12345'
            }

            salesforce.update_approval_specialist_on_application(application=self.application,
                                                                 salesforce_data=salesforce_data)
            self.assertIsNotNone(self.application.approval_specialist)
            self.assertEqual(self.application.approval_specialist.sf_id, 'test12345')
            self.assertEqual(InternalSupportUser.objects.last(), self.application.approval_specialist)

    def test_update_stakeholders(self):
        salesforce_account_trigger_payload = {
            "Agent_s_TC_Email__c": "some-tc-email@homeward.com"
        }

        # adds new TC
        salesforce.update_stakeholders(self.application, salesforce_account_trigger_payload)
        self.application.refresh_from_db()
        self.assertEqual(self.application.stakeholders.count(), 1)
        first_tc = self.application.stakeholders.first()
        self.assertEqual(first_tc.email, "some-tc-email@homeward.com")

        # does not add a new TC if email is same
        salesforce.update_stakeholders(self.application, salesforce_account_trigger_payload)
        self.application.refresh_from_db()
        self.assertEqual(self.application.stakeholders.count(), 1)

        # deletes old and adds new if TC email is different
        salesforce_account_trigger_payload = {
            "Agent_s_TC_Email__c": "new-tc-email@homeward.com"
        }
        salesforce.update_stakeholders(self.application, salesforce_account_trigger_payload)
        self.application.refresh_from_db()
        second_tc = self.application.stakeholders.first()
        self.assertEqual(self.application.stakeholders.count(), 1)
        self.assertEqual(second_tc.email, "new-tc-email@homeward.com")
        self.assertNotEqual(second_tc.id, first_tc.id)

    def test_update_loan_advisor(self):
        with patch.object(salesforce.Salesforce, 'get_user_by_id') as mock_get_user_by_id:
            mock_data = {
                InternalSupportUser.USER_EMAIL: "test.la@homeward.com",
                InternalSupportUser.USER_BIO: "Some BIO...",
                InternalSupportUser.USER_FIRST_NAME: "Test",
                InternalSupportUser.USER_LAST_NAME: "Loan Advisor",
                InternalSupportUser.USER_PHONE: "1111111111",
                InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PROFILE_NAME: "Loan Officer",
                InternalSupportUser.ID_FIELD: "test12345"
            }
            mock_get_user_by_id.return_value = mock_data
            salesforce_account_trigger_payload = {
                InternalSupportUser.LOAN_ADVISOR_ID_FIELD: "test12345"
            }
            salesforce.update_loan_advisor(self.application, salesforce_account_trigger_payload)

            # It should create a new cx manager
            self.assertEqual(InternalSupportUser.objects.all().count(), 1)
            loan_advisor = InternalSupportUser.objects.get(email="test.la@homeward.com")

            # It should update an existing cx manager
        with patch.object(salesforce.Salesforce, 'get_user_by_id') as mock_get_user_by_id:
            mock_data = {
                InternalSupportUser.USER_EMAIL: "test.la@homeward.com",
                InternalSupportUser.USER_BIO: "Some BIO...",
                InternalSupportUser.USER_FIRST_NAME: "Test",
                InternalSupportUser.USER_LAST_NAME: "Loan Advisor",
                InternalSupportUser.USER_PHONE: "2222222222",
                InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
                InternalSupportUser.USER_PROFILE_NAME: "Loan Officer",
                InternalSupportUser.ID_FIELD: "test12345"
            }
            mock_get_user_by_id.return_value = mock_data
            salesforce_account_trigger_payload = {
                InternalSupportUser.LOAN_ADVISOR_ID_FIELD: "test12345"
            }

            salesforce.update_loan_advisor(self.application, salesforce_account_trigger_payload)
            loan_advisor = InternalSupportUser.objects.get(email="test.la@homeward.com")
            self.assertEqual(loan_advisor.phone, "2222222222")
            self.assertEqual(self.application.loan_advisor, loan_advisor)
            self.assertIsNone(self.application.cx_manager)

    def test_should_update_rent_without_prepaid_rent(self):
        mock_data = {
            Rent.RENT_PAYMENT_TYPE_FIELD: 'Monthly',
            Rent.RENT_MONTHLY_RENTAL_RATE: 12345.67,
            Rent.RENT_DAILY_RENTAL_RATE: 145.22
        }
        salesforce.update_rent(self.new_home_purchase, mock_data)
        self.assertEqual(self.new_home_purchase.rent.amount_months_one_and_two, 12345.67)
        self.assertEqual(self.new_home_purchase.rent.daily_rental_rate, 145.22)

        # should not update when required field is missing from salesforce data
        mock_data = {
            Rent.RENT_MONTHLY_RENTAL_RATE: 0.00,
        }
        salesforce.update_rent(self.new_home_purchase, mock_data)
        self.assertEqual(self.new_home_purchase.rent.amount_months_one_and_two, 12345.67)

    def test_should_set_hw_mortgage_candidate(self):
        self.application.hw_mortgage_candidate = None
        mock_data = {
            Application.HW_MORTGAGE_CANDIDATE: 'Yes - Required',
        }
        salesforce.update_application(self.application, mock_data)
        self.assertEqual(self.application.hw_mortgage_candidate, 'Yes - Required')

    @patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
    def test_create_offer_from_salesforce(self, mock_sf):
        application = random_objects.random_application(new_salesforce=str(fake.md5()))

        offer_payload = {
            'Id': str(fake.md5()),
            Offer.STATUS_FIELD: fake.random_element(['Requested', 'EAV Complete', 'Approved',
                                                     'Backup Position Accepted', 'Denied', 'Won', 'Lost',
                                                     'Request Cancelled', 'Contract Cancelled']),
            Offer.YEAR_BUILT_FIELD: fake.year(),
            Offer.HOME_SQUARE_FOOTAGE_FIELD: fake.pyint(max_value=10000),
            Offer.PROPERTY_TYPE_FIELD: fake.random_element(list(PropertyType)),
            Offer.LESS_THAN_ONE_ACRE_FIELD: fake.random_element(['Yes', 'No']),
            Offer.HOME_LIST_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.OFFER_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.CONTRACT_TYPE_FIELD: fake.random_element(list(ContractType)),
            Offer.OTHER_OFFER_FIELD: fake.random_element(list(OtherOffers)),
            Offer.OFFER_DEADLINE_FIELD: fake.date_time_this_month(after_now=True, tzinfo=UTC),
            Offer.LEASE_BACK_TO_SELLER_FIELD: fake.random_element(list(PlanToLeaseBackToSeller)),
            Offer.WAIVE_APPRAISAL_FIELD: fake.random_element(list(WaiveAppraisal)),
            Offer.ALREADY_UNDER_CONTRACT_FIELD: fake.random_element(['Yes', 'No']),
            Offer.CUSTOMER_FIELD: application.new_salesforce,
            Offer.ADDRESS_STREET_FIELD: fake.street_address(),
            Offer.ADDRESS_CITY_FIELD: fake.city(),
            Offer.ADDRESS_STATE_FIELD: fake.state(),
            Offer.ADDRESS_ZIP_FIELD: fake.postcode(),
            Offer.HOMEWARD_ID: None
        }

        salesforce.sync_offer_record_from_salesforce(offer_payload)

        self.assertEqual(Offer.objects.all().count(), 1)

        offer = Offer.objects.first()

        self.assertEqual(offer.application, application)
        self.assertEqual(offer.year_built, int(offer_payload[Offer.YEAR_BUILT_FIELD]))
        self.assertEqual(offer.home_square_footage, offer_payload[Offer.HOME_SQUARE_FOOTAGE_FIELD])
        self.assertEqual(offer.property_type, offer_payload[Offer.PROPERTY_TYPE_FIELD])
        self.assertEqual(offer.less_than_one_acre, offer_payload[Offer.LESS_THAN_ONE_ACRE_FIELD] == 'Yes')
        self.assertEqual(offer.home_list_price, offer_payload[Offer.HOME_LIST_PRICE_FIELD])
        self.assertEqual(offer.offer_price, offer_payload[Offer.OFFER_PRICE_FIELD])
        self.assertEqual(offer.contract_type, offer_payload[Offer.CONTRACT_TYPE_FIELD])
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_deadline, offer_payload[Offer.OFFER_DEADLINE_FIELD])
        self.assertEqual(offer.plan_to_lease_back_to_seller, offer_payload[Offer.LEASE_BACK_TO_SELLER_FIELD])
        self.assertEqual(offer.waive_appraisal, offer_payload[Offer.WAIVE_APPRAISAL_FIELD])
        self.assertEqual(offer.already_under_contract, offer_payload[Offer.ALREADY_UNDER_CONTRACT_FIELD] == 'Yes')
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_property_address.street, offer_payload[Offer.ADDRESS_STREET_FIELD])
        self.assertEqual(offer.offer_property_address.city, offer_payload[Offer.ADDRESS_CITY_FIELD])
        self.assertEqual(offer.offer_property_address.state, offer_payload[Offer.ADDRESS_STATE_FIELD])
        self.assertEqual(offer.offer_property_address.zip, offer_payload[Offer.ADDRESS_ZIP_FIELD])
        self.assertEqual(offer.status, offer_payload[Offer.STATUS_FIELD])
        self.assertEqual(offer.salesforce_id, offer_payload['Id'])
        self.assertIsNotNone(offer.id)

    def test_update_offer_from_salesforce(self):
        application = random_objects.random_application(new_salesforce=str(fake.md5()))
        offer = random_objects.random_offer(application=application, salesforce_id=str(fake.md5()))

        offer_payload = {
            'Id': offer.salesforce_id,
            Offer.STATUS_FIELD: fake.random_element(['Requested', 'EAV Complete', 'Approved',
                                                     'Backup Position Accepted', 'Denied', 'Won', 'Lost',
                                                     'Request Cancelled', 'Contract Cancelled']),
            Offer.YEAR_BUILT_FIELD: fake.year(),
            Offer.HOME_SQUARE_FOOTAGE_FIELD: fake.pyint(max_value=10000),
            Offer.PROPERTY_TYPE_FIELD: fake.random_element(list(PropertyType)),
            Offer.LESS_THAN_ONE_ACRE_FIELD: fake.random_element(['Yes', 'No']),
            Offer.HOME_LIST_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.OFFER_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.CONTRACT_TYPE_FIELD: fake.random_element(list(ContractType)),
            Offer.OTHER_OFFER_FIELD: fake.random_element(list(OtherOffers)),
            Offer.OFFER_DEADLINE_FIELD: fake.date_time_this_month(after_now=True, tzinfo=UTC),
            Offer.LEASE_BACK_TO_SELLER_FIELD: fake.random_element(list(PlanToLeaseBackToSeller)),
            Offer.WAIVE_APPRAISAL_FIELD: fake.random_element(list(WaiveAppraisal)),
            Offer.ALREADY_UNDER_CONTRACT_FIELD: fake.random_element(['Yes', 'No']),
            Offer.CUSTOMER_FIELD: application.new_salesforce,
            Offer.ADDRESS_STREET_FIELD: fake.street_address(),
            Offer.ADDRESS_CITY_FIELD: fake.city(),
            Offer.ADDRESS_STATE_FIELD: fake.state(),
            Offer.ADDRESS_ZIP_FIELD: fake.postcode(),
            Offer.FINANCE_APPROVED_CLOSE_DATE: "2021-03-02",
            Offer.FUNDING_TYPE: "Pure Cash: Double Close",
            Offer.HOMEWARD_ID: offer.id
        }

        salesforce.sync_offer_record_from_salesforce(offer_payload)

        self.assertEqual(Offer.objects.all().count(), 1)

        offer.refresh_from_db()
        self.assertEqual(offer.application, application)
        self.assertEqual(offer.year_built, int(offer_payload[Offer.YEAR_BUILT_FIELD]))
        self.assertEqual(offer.home_square_footage, offer_payload[Offer.HOME_SQUARE_FOOTAGE_FIELD])
        self.assertEqual(offer.property_type, offer_payload[Offer.PROPERTY_TYPE_FIELD])
        self.assertEqual(offer.less_than_one_acre, offer_payload[Offer.LESS_THAN_ONE_ACRE_FIELD] == 'Yes')
        self.assertEqual(offer.home_list_price, offer_payload[Offer.HOME_LIST_PRICE_FIELD])
        self.assertEqual(offer.offer_price, offer_payload[Offer.OFFER_PRICE_FIELD])
        self.assertEqual(offer.contract_type, offer_payload[Offer.CONTRACT_TYPE_FIELD])
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_deadline, offer_payload[Offer.OFFER_DEADLINE_FIELD])
        self.assertEqual(offer.plan_to_lease_back_to_seller, offer_payload[Offer.LEASE_BACK_TO_SELLER_FIELD])
        self.assertEqual(offer.waive_appraisal, offer_payload[Offer.WAIVE_APPRAISAL_FIELD])
        self.assertEqual(offer.already_under_contract, offer_payload[Offer.ALREADY_UNDER_CONTRACT_FIELD] == 'Yes')
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_property_address.street, offer_payload[Offer.ADDRESS_STREET_FIELD])
        self.assertEqual(offer.offer_property_address.city, offer_payload[Offer.ADDRESS_CITY_FIELD])
        self.assertEqual(offer.offer_property_address.state, offer_payload[Offer.ADDRESS_STATE_FIELD])
        self.assertEqual(offer.offer_property_address.zip, offer_payload[Offer.ADDRESS_ZIP_FIELD])
        self.assertEqual(offer.status, offer_payload[Offer.STATUS_FIELD])
        self.assertEqual(offer.salesforce_id, offer_payload['Id'])
        self.assertEqual(offer.finance_approved_close_date.isoformat(), offer_payload[Offer.FINANCE_APPROVED_CLOSE_DATE])
        self.assertEqual(offer.funding_type, "Pure Cash: Double Close")
        self.assertEqual(offer.id, offer_payload[Offer.HOMEWARD_ID])

    @patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
    def test_create_rent_from_salesforce(self, mock_sf):
        application = random_objects.random_application(new_salesforce='A1BCD')
        nhp = NewHomePurchase.objects.create()
        application.new_home_purchase = nhp
        application.save()

        rent_count = Rent.objects.all().count()

        rent_payload = {
            'Customer__c': 'A1BCD',
            Rent.RENT_PAYMENT_TYPE_FIELD: 'Deferred',
            Rent.RENT_DAILY_RENTAL_RATE: fake.pyint(max_value=100),
            Rent.RENT_MONTHLY_RENTAL_RATE: fake.random_int(min=5400, max=10000),
            Rent.RENT_STOP_DATE: fake.date_this_month(after_today=True),
            Rent.RENT_TOTAL_WAIVED_RENT: fake.pyint(max_value=500),
            Rent.RENT_TOTAL_LEASEBACK_CREDIT: fake.pyint(max_value=500)
        }

        salesforce.sync_customer_purchase_record_from_salesforce(rent_payload)

        self.assertEqual(Rent.objects.all().count(), (rent_count + 1))

        application.refresh_from_db()

        rent = application.new_home_purchase.rent

        self.assertEqual(rent.type, 'Deferred')
        self.assertEqual(rent.daily_rental_rate, int(rent_payload[Rent.RENT_DAILY_RENTAL_RATE]))
        self.assertEqual(rent.amount_months_one_and_two, int(rent_payload[Rent.RENT_MONTHLY_RENTAL_RATE]))
        self.assertEqual(rent.stop_rent_date, rent_payload[Rent.RENT_STOP_DATE])
        self.assertEqual(rent.total_waived_rent, int(rent_payload[Rent.RENT_TOTAL_WAIVED_RENT]))
        self.assertEqual(rent.total_leaseback_credit, int(rent_payload[Rent.RENT_TOTAL_LEASEBACK_CREDIT]))

    def test_update_rent_from_salesforce(self):
        application = random_objects.random_application(new_salesforce='A1BCD',
                                                        new_home_purchase=random_objects.random_new_home_purchase())

        rent = application.new_home_purchase.rent
        rent_count = Rent.objects.all().count()

        rent_payload = {
            'Customer__c': 'A1BCD',
            Rent.RENT_PAYMENT_TYPE_FIELD: 'Deferred',
            Rent.RENT_DAILY_RENTAL_RATE: fake.pyint(max_value=100),
            Rent.RENT_MONTHLY_RENTAL_RATE: fake.random_int(min=5400, max=10000),
            Rent.RENT_STOP_DATE: fake.date_this_month(after_today=True),
            Rent.RENT_TOTAL_WAIVED_RENT: fake.pyint(max_value=500),
            Rent.RENT_TOTAL_LEASEBACK_CREDIT: fake.pyint(max_value=500)
        }

        salesforce.sync_customer_purchase_record_from_salesforce(rent_payload)

        self.assertEqual(Rent.objects.all().count(), rent_count)

        rent.refresh_from_db()

        self.assertEqual(rent.type, 'Deferred')
        self.assertEqual(rent.daily_rental_rate, int(rent_payload[Rent.RENT_DAILY_RENTAL_RATE]))
        self.assertEqual(rent.amount_months_one_and_two, int(rent_payload[Rent.RENT_MONTHLY_RENTAL_RATE]))
        self.assertEqual(rent.stop_rent_date, rent_payload[Rent.RENT_STOP_DATE])
        self.assertEqual(rent.total_waived_rent, int(rent_payload[Rent.RENT_TOTAL_WAIVED_RENT]))
        self.assertEqual(rent.total_leaseback_credit, int(rent_payload[Rent.RENT_TOTAL_LEASEBACK_CREDIT]))

    @patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
    def test_create_offer_transaction_from_salesforce(self, mock_sf):
        application = random_objects.random_application(new_salesforce=str(fake.md5()))

        offer_payload = {
            Offer.OFFER_SALESFORCE_ID: str(fake.md5()),
            Offer.OFFER_TRANSACTION_ID: None,
            NewHomePurchase.TRANSACTION_RECORD_TYPE: constants.OFFER_TRANSACTION,
            Offer.STATUS_FIELD: fake.random_element(['Requested', 'EAV Complete', 'Approved',
                                                     'Backup Position Accepted', 'Denied', 'Won', 'Lost',
                                                     'Request Cancelled', 'Contract Cancelled']),
            Offer.YEAR_BUILT_FIELD: fake.year(),
            Offer.HOME_SQUARE_FOOTAGE_FIELD: fake.pyint(max_value=10000),
            Offer.PROPERTY_TYPE_FIELD: fake.random_element(list(PropertyType)),
            Offer.LESS_THAN_ONE_ACRE_FIELD: fake.random_element(['Yes', 'No']),
            Offer.HOME_LIST_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.OFFER_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.CONTRACT_TYPE_FIELD: fake.random_element(list(ContractType)),
            Offer.OTHER_OFFER_FIELD: fake.random_element(list(OtherOffers)),
            Offer.OFFER_DEADLINE_FIELD: fake.date_time_this_month(after_now=True, tzinfo=UTC),
            Offer.LEASE_BACK_TO_SELLER_FIELD: fake.random_element(list(PlanToLeaseBackToSeller)),
            Offer.WAIVE_APPRAISAL_FIELD: fake.random_element(list(WaiveAppraisal)),
            Offer.ALREADY_UNDER_CONTRACT_FIELD: fake.random_element(['Yes', 'No']),
            Offer.CUSTOMER_FIELD: application.new_salesforce,
            Offer.ADDRESS_STREET_FIELD: fake.street_address(),
            Offer.ADDRESS_CITY_FIELD: fake.city(),
            Offer.ADDRESS_STATE_FIELD: fake.state(),
            Offer.ADDRESS_ZIP_FIELD: fake.postcode(),
            Offer.HOMEWARD_ID: None
        }

        salesforce.sync_transaction_record_from_salesforce(offer_payload)

        self.assertEqual(Offer.objects.all().count(), 1)

        offer = Offer.objects.first()

        self.assertEqual(offer.application, application)
        self.assertEqual(offer.year_built, int(offer_payload[Offer.YEAR_BUILT_FIELD]))
        self.assertEqual(offer.home_square_footage, offer_payload[Offer.HOME_SQUARE_FOOTAGE_FIELD])
        self.assertEqual(offer.property_type, offer_payload[Offer.PROPERTY_TYPE_FIELD])
        self.assertEqual(offer.less_than_one_acre, offer_payload[Offer.LESS_THAN_ONE_ACRE_FIELD] == 'Yes')
        self.assertEqual(offer.home_list_price, offer_payload[Offer.HOME_LIST_PRICE_FIELD])
        self.assertEqual(offer.offer_price, offer_payload[Offer.OFFER_PRICE_FIELD])
        self.assertEqual(offer.contract_type, offer_payload[Offer.CONTRACT_TYPE_FIELD])
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_deadline, offer_payload[Offer.OFFER_DEADLINE_FIELD])
        self.assertEqual(offer.plan_to_lease_back_to_seller, offer_payload[Offer.LEASE_BACK_TO_SELLER_FIELD])
        self.assertEqual(offer.waive_appraisal, offer_payload[Offer.WAIVE_APPRAISAL_FIELD])
        self.assertEqual(offer.already_under_contract, offer_payload[Offer.ALREADY_UNDER_CONTRACT_FIELD] == 'Yes')
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_property_address.street, offer_payload[Offer.ADDRESS_STREET_FIELD])
        self.assertEqual(offer.offer_property_address.city, offer_payload[Offer.ADDRESS_CITY_FIELD])
        self.assertEqual(offer.offer_property_address.state, offer_payload[Offer.ADDRESS_STATE_FIELD])
        self.assertEqual(offer.offer_property_address.zip, offer_payload[Offer.ADDRESS_ZIP_FIELD])
        self.assertEqual(offer.status, offer_payload[Offer.STATUS_FIELD])
        self.assertEqual(offer.salesforce_id, offer_payload['Id'])
        self.assertIsNotNone(offer.id)

    def test_update_offer_transaction_from_salesforce(self):
        application = random_objects.random_application(new_salesforce=str(fake.md5()))
        offer = random_objects.random_offer(application=application, salesforce_id=str(fake.md5()))

        offer_payload = {
            Offer.OFFER_SALESFORCE_ID: offer.salesforce_id,
            Offer.OFFER_TRANSACTION_ID: None,
            NewHomePurchase.TRANSACTION_RECORD_TYPE: constants.OFFER_TRANSACTION,
            Offer.STATUS_FIELD: fake.random_element(['Requested', 'EAV Complete', 'Approved',
                                                     'Backup Position Accepted', 'Denied', 'Won', 'Lost',
                                                     'Request Cancelled', 'Contract Cancelled']),
            Offer.YEAR_BUILT_FIELD: fake.year(),
            Offer.HOME_SQUARE_FOOTAGE_FIELD: fake.pyint(max_value=10000),
            Offer.PROPERTY_TYPE_FIELD: fake.random_element(list(PropertyType)),
            Offer.LESS_THAN_ONE_ACRE_FIELD: fake.random_element(['Yes', 'No']),
            Offer.HOME_LIST_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.OFFER_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.CONTRACT_TYPE_FIELD: fake.random_element(list(ContractType)),
            Offer.OTHER_OFFER_FIELD: fake.random_element(list(OtherOffers)),
            Offer.OFFER_DEADLINE_FIELD: fake.date_time_this_month(after_now=True, tzinfo=UTC),
            Offer.LEASE_BACK_TO_SELLER_FIELD: fake.random_element(list(PlanToLeaseBackToSeller)),
            Offer.WAIVE_APPRAISAL_FIELD: fake.random_element(list(WaiveAppraisal)),
            Offer.ALREADY_UNDER_CONTRACT_FIELD: fake.random_element(['Yes', 'No']),
            Offer.CUSTOMER_FIELD: application.new_salesforce,
            Offer.ADDRESS_STREET_FIELD: fake.street_address(),
            Offer.ADDRESS_CITY_FIELD: fake.city(),
            Offer.ADDRESS_STATE_FIELD: fake.state(),
            Offer.ADDRESS_ZIP_FIELD: fake.postcode(),
            Offer.FINANCE_APPROVED_CLOSE_DATE: "2021-03-02",
            Offer.FUNDING_TYPE: "Pure Cash: Double Close",
            Offer.HOMEWARD_ID: offer.id
        }

        salesforce.sync_transaction_record_from_salesforce(offer_payload)

        self.assertEqual(Offer.objects.all().count(), 1)

        offer.refresh_from_db()

        self.assertEqual(offer.application, application)
        self.assertEqual(offer.year_built, int(offer_payload[Offer.YEAR_BUILT_FIELD]))
        self.assertEqual(offer.home_square_footage, offer_payload[Offer.HOME_SQUARE_FOOTAGE_FIELD])
        self.assertEqual(offer.property_type, offer_payload[Offer.PROPERTY_TYPE_FIELD])
        self.assertEqual(offer.less_than_one_acre, offer_payload[Offer.LESS_THAN_ONE_ACRE_FIELD] == 'Yes')
        self.assertEqual(offer.home_list_price, offer_payload[Offer.HOME_LIST_PRICE_FIELD])
        self.assertEqual(offer.offer_price, offer_payload[Offer.OFFER_PRICE_FIELD])
        self.assertEqual(offer.contract_type, offer_payload[Offer.CONTRACT_TYPE_FIELD])
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_deadline, offer_payload[Offer.OFFER_DEADLINE_FIELD])
        self.assertEqual(offer.plan_to_lease_back_to_seller, offer_payload[Offer.LEASE_BACK_TO_SELLER_FIELD])
        self.assertEqual(offer.waive_appraisal, offer_payload[Offer.WAIVE_APPRAISAL_FIELD])
        self.assertEqual(offer.already_under_contract, offer_payload[Offer.ALREADY_UNDER_CONTRACT_FIELD] == 'Yes')
        self.assertEqual(offer.other_offers, offer_payload[Offer.OTHER_OFFER_FIELD])
        self.assertEqual(offer.offer_property_address.street, offer_payload[Offer.ADDRESS_STREET_FIELD])
        self.assertEqual(offer.offer_property_address.city, offer_payload[Offer.ADDRESS_CITY_FIELD])
        self.assertEqual(offer.offer_property_address.state, offer_payload[Offer.ADDRESS_STATE_FIELD])
        self.assertEqual(offer.offer_property_address.zip, offer_payload[Offer.ADDRESS_ZIP_FIELD])
        self.assertEqual(offer.status, offer_payload[Offer.STATUS_FIELD])
        self.assertEqual(offer.salesforce_id, offer_payload['Id'])
        self.assertEqual(offer.finance_approved_close_date.isoformat(), offer_payload[Offer.FINANCE_APPROVED_CLOSE_DATE])
        self.assertEqual(offer.funding_type, "Pure Cash: Double Close")
        self.assertEqual(offer.id, offer_payload[Offer.HOMEWARD_ID])

    @patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
    def test_create_homeward_purchase_from_salesforce(self, mock_sf):
        application = random_objects.random_application(new_salesforce='A1BCD')
        offer = random_objects.random_offer(application=application, salesforce_id='bloop')

        nhps = NewHomePurchase.objects.all().count()

        homeward_purchase_payload = {
            Offer.OFFER_SALESFORCE_ID: str(fake.md5()),
            Offer.OFFER_TRANSACTION_ID: offer.salesforce_id,
            NewHomePurchase.TRANSACTION_RECORD_TYPE: constants.HOMEWARD_PURCHASE_TRANSACTION,
            NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE: date.today(),
            NewHomePurchase.OPTION_END_DATE_FIELD: date.today(),
            NewHomePurchase.CONTRACT_PRICE_TRANSACTION_FIELD: 350000,
            NewHomePurchase.EARNEST_DEPOSIT_PERCENTAGE_FIELD: 2.0,
            NewHomePurchase.NEW_HOME_PURCHASE_STATUS: "Offer Won",
            NewHomePurchase.REASSIGNED_CONTRACT_FIELD: False
        }

        salesforce.sync_transaction_record_from_salesforce(homeward_purchase_payload)

        self.assertEqual(NewHomePurchase.objects.all().count(), (nhps + 1))

        offer.refresh_from_db()

        nhp = offer.new_home_purchase

        self.assertEqual(nhp.homeward_purchase_close_date, homeward_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE])
        self.assertEqual(nhp.option_period_end_date, homeward_purchase_payload[NewHomePurchase.OPTION_END_DATE_FIELD])
        self.assertEqual(nhp.contract_price, int(homeward_purchase_payload[NewHomePurchase.CONTRACT_PRICE_TRANSACTION_FIELD]))
        self.assertEqual(nhp.earnest_deposit_percentage, int(homeward_purchase_payload[NewHomePurchase.EARNEST_DEPOSIT_PERCENTAGE_FIELD]))
        self.assertEqual(nhp.homeward_purchase_status, homeward_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_STATUS])
        self.assertEqual(nhp.is_reassigned_contract, homeward_purchase_payload[NewHomePurchase.REASSIGNED_CONTRACT_FIELD])

    def test_update_homeward_purchase_from_salesforce(self):
        application = random_objects.random_application(new_salesforce='A1BCD')

        offer = random_objects.random_offer(application=application,
                                            new_home_purchase=random_objects.random_new_home_purchase(),
                                            salesforce_id='bloop')

        nhps = NewHomePurchase.objects.all().count()

        homeward_purchase_payload = {
            Offer.OFFER_SALESFORCE_ID: str(fake.md5()),
            Offer.OFFER_TRANSACTION_ID: offer.salesforce_id,
            NewHomePurchase.TRANSACTION_RECORD_TYPE: constants.HOMEWARD_PURCHASE_TRANSACTION,
            NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE: date.today(),
            NewHomePurchase.OPTION_END_DATE_FIELD: date.today(),
            NewHomePurchase.CONTRACT_PRICE_TRANSACTION_FIELD: 350000,
            NewHomePurchase.EARNEST_DEPOSIT_PERCENTAGE_FIELD: 2.0,
            NewHomePurchase.NEW_HOME_PURCHASE_STATUS: "Offer Won",
            NewHomePurchase.REASSIGNED_CONTRACT_FIELD: False
        }

        salesforce.sync_transaction_record_from_salesforce(homeward_purchase_payload)

        self.assertEqual(NewHomePurchase.objects.all().count(), nhps)

        offer.refresh_from_db()

        nhp = offer.new_home_purchase

        self.assertEqual(nhp.homeward_purchase_close_date, homeward_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE])
        self.assertEqual(nhp.option_period_end_date, homeward_purchase_payload[NewHomePurchase.OPTION_END_DATE_FIELD])
        self.assertEqual(nhp.contract_price, int(homeward_purchase_payload[NewHomePurchase.CONTRACT_PRICE_TRANSACTION_FIELD]))
        self.assertEqual(nhp.earnest_deposit_percentage, int(homeward_purchase_payload[NewHomePurchase.EARNEST_DEPOSIT_PERCENTAGE_FIELD]))
        self.assertEqual(nhp.homeward_purchase_status, homeward_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_STATUS])
        self.assertEqual(nhp.is_reassigned_contract, homeward_purchase_payload[NewHomePurchase.REASSIGNED_CONTRACT_FIELD])

    @patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
    def test_create_customer_purchase_fields_from_salesforce(self, mock_sf):
        application = random_objects.random_application(new_salesforce='A1BCD')
        offer = random_objects.random_offer(application=application,
                                            salesforce_id='blah')
        nhp = NewHomePurchase.objects.create()
        offer.new_home_purchase = nhp
        offer.save()

        rent_count = Rent.objects.all().count()

        customer_purchase_payload = {
            Offer.OFFER_SALESFORCE_ID: str(fake.md5()),
            Offer.OFFER_TRANSACTION_ID: offer.salesforce_id,
            NewHomePurchase.TRANSACTION_RECORD_TYPE: constants.CUSTOMER_PURCHASE_TRANSACTION,
            Rent.RENT_PAYMENT_TYPE_FIELD: 'Deferred',
            Rent.RENT_DAILY_RENTAL_RATE: fake.pyint(max_value=100),
            Rent.RENT_MONTHLY_RENTAL_RATE: fake.random_int(min=5400, max=10000),
            Rent.RENT_STOP_DATE: fake.date_this_month(after_today=True),
            Rent.RENT_TOTAL_WAIVED_RENT: fake.pyint(max_value=500),
            Rent.RENT_TOTAL_LEASEBACK_CREDIT: fake.pyint(max_value=500),
            NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE: date.today(),
            NewHomePurchase.NEW_HOME_PURCHASE_STATUS: "Homeward Purchase"
        }

        salesforce.sync_transaction_record_from_salesforce(customer_purchase_payload)

        self.assertEqual(Rent.objects.all().count(), (rent_count + 1))

        offer.refresh_from_db()

        rent = offer.new_home_purchase.rent

        self.assertEqual(rent.type, 'Deferred')
        self.assertEqual(rent.daily_rental_rate, int(customer_purchase_payload[Rent.RENT_DAILY_RENTAL_RATE]))
        self.assertEqual(rent.amount_months_one_and_two, int(customer_purchase_payload[Rent.RENT_MONTHLY_RENTAL_RATE]))
        self.assertEqual(rent.stop_rent_date, customer_purchase_payload[Rent.RENT_STOP_DATE])
        self.assertEqual(rent.total_waived_rent, int(customer_purchase_payload[Rent.RENT_TOTAL_WAIVED_RENT]))
        self.assertEqual(rent.total_leaseback_credit, int(customer_purchase_payload[Rent.RENT_TOTAL_LEASEBACK_CREDIT]))
        self.assertEqual(offer.new_home_purchase.customer_purchase_close_date, customer_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE])
        self.assertEqual(offer.new_home_purchase.customer_purchase_status, customer_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_STATUS])

    def test_update_customer_purchase_fields_from_salesforce(self):
        application = random_objects.random_application(new_salesforce='A1BCD')
        offer = random_objects.random_offer(application=application,
                                            salesforce_id='blah')
        nhp = NewHomePurchase.objects.create(rent=random_objects.random_rent())
        offer.new_home_purchase = nhp
        offer.save()

        rent = offer.new_home_purchase.rent
        rent_count = Rent.objects.all().count()

        customer_purchase_payload = {
            Offer.OFFER_SALESFORCE_ID: str(fake.md5()),
            Offer.OFFER_TRANSACTION_ID: offer.salesforce_id,
            NewHomePurchase.TRANSACTION_RECORD_TYPE: constants.CUSTOMER_PURCHASE_TRANSACTION,
            Rent.RENT_PAYMENT_TYPE_FIELD: 'Deferred',
            Rent.RENT_DAILY_RENTAL_RATE: fake.pyint(max_value=100),
            Rent.RENT_MONTHLY_RENTAL_RATE: fake.random_int(min=5400, max=10000),
            Rent.RENT_STOP_DATE: fake.date_this_month(after_today=True),
            Rent.RENT_TOTAL_WAIVED_RENT: fake.pyint(max_value=500),
            Rent.RENT_TOTAL_LEASEBACK_CREDIT: fake.pyint(max_value=500),
            NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE: date.today(),
            NewHomePurchase.NEW_HOME_PURCHASE_STATUS: "Homeward Purchase"
        }

        salesforce.sync_transaction_record_from_salesforce(customer_purchase_payload)

        self.assertEqual(Rent.objects.all().count(), rent_count)

        rent.refresh_from_db()
        offer.refresh_from_db()

        self.assertEqual(rent.type, 'Deferred')
        self.assertEqual(rent.daily_rental_rate, int(customer_purchase_payload[Rent.RENT_DAILY_RENTAL_RATE]))
        self.assertEqual(rent.amount_months_one_and_two, int(customer_purchase_payload[Rent.RENT_MONTHLY_RENTAL_RATE]))
        self.assertEqual(rent.stop_rent_date, customer_purchase_payload[Rent.RENT_STOP_DATE])
        self.assertEqual(rent.total_waived_rent, int(customer_purchase_payload[Rent.RENT_TOTAL_WAIVED_RENT]))
        self.assertEqual(rent.total_leaseback_credit, int(customer_purchase_payload[Rent.RENT_TOTAL_LEASEBACK_CREDIT]))
        self.assertEqual(offer.new_home_purchase.customer_purchase_close_date, customer_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE])
        self.assertEqual(offer.new_home_purchase.customer_purchase_status, customer_purchase_payload[NewHomePurchase.NEW_HOME_PURCHASE_STATUS])
