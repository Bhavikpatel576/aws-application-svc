import uuid
from datetime import datetime, timedelta, date
from unittest import mock
from unittest.mock import patch

import pytz
from dateutil import parser
from dateutil.relativedelta import relativedelta, MO, SA
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework.test import APITestCase

from api.v1_0_0.tests._utils import data_generators
from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.address import Address
from application.models.application import Application, ApplicationStage, ProductOffering
from application.models.contract_template import ContractTemplate, BuyingState
from application.models.offer import Offer, PlanToLeaseBackToSeller, WaiveAppraisal, OtherOffers, ContractType, \
    PropertyType, OfferStatus
from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects
from application.tests.random_objects import fake
from src.utils import date_restrictor
from utils.date_restrictor import MAXIMUM_CLOSING_CAPACITY


class OfferTests(AuthMixin, APITestCase):
    def setUp(self):
        self.user = self.create_user("fake_agent_user1")
        self.token = self.login_user(self.user)[1]
        self.headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }
        self.agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=self.user.email))
        self.application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        self.application.buying_agent = self.agent
        self.application.product_offering = 'buy-only'
        self.application.save()

        self.request_data = {
                'year_built': 2012,
                'home_square_footage': 1300,
                'property_type': 'Single Family',
                'less_than_one_acre': True,
                'home_list_price': 500000,
                "offer_price": 510000,
                "contract_type": "Resale",
                "other_offers": "1-4",
                "offer_deadline": timezone.now(),
                "plan_to_lease_back_to_seller": "No",
                "waive_appraisal": 'No - undecided on covering delta & wants to know value first',
                "already_under_contract": True,
                "comments": "test comments",
                "application_id": self.application.id,
                "preferred_closing_date": "2020-09-30",
                "offer_property_address": {
                    "street": "2222 Test St.",
                    "city": "Austin",
                    "state": "TX",
                    "zip": 78704
                }
            }

    def assertIsoFormattedDate(self, text):
        self.assertRegex(text, r'^(\d{4})-(\d{2})-(\d{2})$')

    @mock.patch('utils.date_restrictor.calculate_dates_at_capacity')
    def test_should_create_offer(self, date_restrictor_patch):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            date_restrictor_patch.return_value = []

            self.agent.email = self.agent.email.upper()
            self.agent.save()
            url = '/api/1.0.0/offer/'

            offers = Offer.objects.all()
            offers_count = offers.count()
            address_count = Address.objects.all().count()

            preferred_closing_date = date(2022, 9, 23)
            self.request_data['preferred_closing_date'] = preferred_closing_date

            response = self.client.post(url, self.request_data, **self.headers, format='json')

            json_response = response.json()

            self.assertEqual(response.status_code, 201, response.content)
            self.assertEqual(json_response["property_type"], "Single Family")
            self.assertEqual(json_response["status"], "Incomplete")
            self.assertEqual(json_response["offer_source"], "dashboard")
            self.assertEqual(json_response["preferred_closing_date"], preferred_closing_date.isoformat())
            self.assertIsNotNone(json_response["created_at"])
            self.assertIsNotNone(json_response["updated_at"])
            self.assertEqual(Offer.objects.all().count(), offers_count+1)
            self.assertEqual(Address.objects.all().count(), address_count+1)

    def test_create_endpoint_no_perms(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedNoGroupsUserReponse()
            url =('/api/1.0.0/offer/')
            user = self.create_user("fake_user1")
            token = self.login_user(user)[1]
            headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            response = self.client.post(url, self.request_data, **headers, format='json')
            self.assertEqual(response.status_code, 403)

    def test_create_endpoint_without_login(self):
        url =('/api/1.0.0/offer/')

        response = self.client.post(url, self.request_data, format='json')
        self.assertEqual(response.status_code, 401)

    def test_will_not_create_without_application(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            url =('/api/1.0.0/offer/')

            request_data_two = {
                'year_built': 2012,
                'home_square_footage': 1300,
                'property_type': 'single family',
                'less_than_one_acre': True,
                'home_list_price': 500000,
                "offer_price": 510000,
                "contract_type": "resale",
                "other_offers": "under five",
                "offer_deadline": timezone.now(),
                "plan_to_lease_back_to_seller": "no",
                "waive_appraisal": False,
                "already_under_contract": True,
                "comments": "test comments",
                "offer_property_address": {
                    "street": "2222 Test St.",
                    "city": "Austin",
                    "state": "TX",
                    "zip": 78704
                }
            }

        response = self.client.post(url, request_data_two, **self.headers, format='json')

        self.assertEqual(response.status_code, 403)

    def test_will_not_create_if_agent_submitting_is_not_application_buying_agent(self):
        with patch("user.models.requests.get") as m:

            m.return_value = data_generators.MockedAgentUserResponse()
            another_user = self.create_user("fake_agent_user2")
            another_token = self.login_user(another_user)[1]
            new_headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(another_token)
            }

            url =('/api/1.0.0/offer/')

            offers = Offer.objects.all()
            response = self.client.post(url, self.request_data, **new_headers, format='json')
            json_response = response.json()

            self.assertEqual(response.status_code, 403)
            self.assertEqual(json_response['detail'], 'You do not have permission to perform this action.')

    def test_will_update_an_offer(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_agent_user3")
            token = self.login_user(user)[1]
            headers = {
                    'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email.upper()))
            application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
            application.buying_agent = agent
            application.save()

            offer = random_objects.random_offer(application=application)
            
            url = '/api/1.0.0/offer/{}/'.format(offer.id)

            data = {
                "year_built": "2020"
            }

            response = self.client.patch(url, data, **headers, format='json')
            json_response = response.json()

            offer = Offer.objects.get(id=json_response["id"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(offer.year_built, 2020)

    @mock.patch('user.models.requests.get')
    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_will_update_an_offer_with_pda_listing_uuid(self, pda, m):
        m.return_value = data_generators.MockedAgentUserResponse()
        user = self.create_user("fake_agent_user3")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent", email=user.email.upper()))
        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        application.buying_agent = agent
        application.save()

        offer = random_objects.random_offer(application=application)

        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "id": pda_listing_uuid,
            "year_built": 1984,
            "square_feet": 1945,
            "acres": 2.3,
            "listing_price": 123456.78,
            'listing_id': '1106009',
            "display_address": "123 Main St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78731"
        }

        pda().get_listing.return_value = fake_listing_data

        offer.pda_listing_uuid = pda_listing_uuid
        offer.save()

        url = '/api/1.0.0/offer/{}/'.format(offer.id)

        data = {
            "year_built": "2020"
        }

        response = self.client.patch(url, data, **headers, format='json')
        json_response = response.json()

        offer = Offer.objects.get(id=json_response["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(offer.year_built, 2020)

    @mock.patch('user.models.requests.get')
    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_will_update_offer_with_new_listing_info(self, pda, m):
        m.return_value = data_generators.MockedAgentUserResponse()
        user = self.create_user("fake_agent_user3")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent", email=user.email.upper()))
        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        application.buying_agent = agent
        application.save()

        offer = random_objects.random_offer(application=application)

        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "year_built": 2003,
            "square_feet": 1790,
            "photo_url": "www.photofake.yeh",
            "total_bedrooms": 4,
            "total_bathrooms": 3,
            "acres": 0.8,
            "listing_price": 289000,
            'listing_id': '1143578',
            "display_address": "123 Test St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78731"
        }

        pda().get_listing.return_value = fake_listing_data

        offer.pda_listing_uuid = pda_listing_uuid
        offer.save()

        self.assertEqual(offer.pda_listing_uuid, pda_listing_uuid)
        self.assertEqual(offer.year_built, 2003)
        self.assertEqual(offer.home_square_footage, 1790)
        self.assertEqual(offer.photo_url, "www.photofake.yeh")
        self.assertEqual(offer.bedrooms, 4)
        self.assertEqual(offer.bathrooms, 3)
        self.assertEqual(offer.less_than_one_acre, True)
        self.assertEqual(offer.home_list_price, 289000)
        self.assertEqual(offer.mls_listing_id, "1143578")
        self.assertEqual(offer.offer_property_address.street, "123 Test St.")
        self.assertEqual(offer.offer_property_address.city, "Austin")
        self.assertEqual(offer.offer_property_address.state, "TX")
        self.assertEqual(offer.offer_property_address.zip, "78731")

        new_pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "year_built": 2001,
            "square_feet": 1900,
            "photo_url": "www.photofake.yah",
            "total_bedrooms": 3,
            "total_bathrooms": 2,
            "acres": 2.3,
            "listing_price": 399000,
            'listing_id': '11061102',
            "display_address": "789 Lake St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78745"
        }

        pda().get_listing.return_value = fake_listing_data

        url = '/api/1.0.0/offer/{}/'.format(offer.id)

        data = {
            "application_id": offer.application.id,
            "pda_listing_uuid": new_pda_listing_uuid
        }

        response = self.client.patch(url, data, **headers, format='json')
        json_response = response.json()

        offer = Offer.objects.get(id=json_response["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(offer.pda_listing_uuid, new_pda_listing_uuid)
        self.assertEqual(offer.year_built, 2001)
        self.assertEqual(offer.home_square_footage, 1900)
        self.assertEqual(offer.photo_url, "www.photofake.yah")
        self.assertEqual(offer.bedrooms, 3)
        self.assertEqual(offer.bathrooms, 2)
        self.assertEqual(offer.less_than_one_acre, False)
        self.assertEqual(offer.home_list_price, 399000)
        self.assertEqual(offer.mls_listing_id, "11061102")
        self.assertEqual(offer.offer_property_address.street, "789 Lake St.")
        self.assertEqual(offer.offer_property_address.city, "Austin")
        self.assertEqual(offer.offer_property_address.state, "TX")
        self.assertEqual(offer.offer_property_address.zip, "78745")

    @mock.patch('user.models.requests.get')
    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_will_update_offer_with_new_listing_info_missing_fields(self, pda, m):
        m.return_value = data_generators.MockedAgentUserResponse()
        user = self.create_user("fake_agent_user3")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent", email=user.email.upper()))
        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        application.buying_agent = agent
        application.save()

        offer = random_objects.random_offer(application=application)

        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "year_built": 2003,
            "square_feet": 1790,
            "photo_url": "www.photofake.yeh",
            "total_bedrooms": 4,
            "total_bathrooms": 3,
            "acres": 0.8,
            "listing_price": 289000,
            'listing_id': '1143578',
            "display_address": "123 Test St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78731"
        }

        pda().get_listing.return_value = fake_listing_data

        offer.pda_listing_uuid = pda_listing_uuid
        offer.save()

        self.assertEqual(offer.pda_listing_uuid, pda_listing_uuid)

        new_pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "year_built": 2001,
            "square_feet": 1900,
            "photo_url": "",
            "total_bedrooms": 3,
            "listing_price": 399000,
            'listing_id': '11061102',
            "display_address": "789 Lake St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78745"
        }

        pda().get_listing.return_value = fake_listing_data

        url = '/api/1.0.0/offer/{}/'.format(offer.id)

        data = {
            "application_id": offer.application.id,
            "pda_listing_uuid": new_pda_listing_uuid
        }

        response = self.client.patch(url, data, **headers, format='json')
        json_response = response.json()

        offer = Offer.objects.get(id=json_response["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(offer.pda_listing_uuid, new_pda_listing_uuid)
        self.assertEqual(offer.year_built, 2001)
        self.assertEqual(offer.home_square_footage, 1900)
        self.assertEqual(offer.photo_url, "")
        self.assertEqual(offer.bedrooms, 3)
        self.assertEqual(offer.bathrooms, None)
        self.assertEqual(offer.less_than_one_acre, None)
        self.assertEqual(offer.home_list_price, 399000)
        self.assertEqual(offer.mls_listing_id, "11061102")
        self.assertEqual(offer.offer_property_address.street, "789 Lake St.")
        self.assertEqual(offer.offer_property_address.city, "Austin")
        self.assertEqual(offer.offer_property_address.state, "TX")
        self.assertEqual(offer.offer_property_address.zip, "78745")

    @mock.patch('user.models.requests.get')
    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_will_update_offer_by_clearing_out_listing_info(self, pda, m):
        m.return_value = data_generators.MockedAgentUserResponse()
        user = self.create_user("fake_agent_user3")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent", email=user.email.upper()))
        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        application.buying_agent = agent
        application.save()

        offer = random_objects.random_offer(application=application)

        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "year_built": 2003,
            "square_feet": 1790,
            "photo_url": "www.photofake.yeh",
            "total_bedrooms": 4,
            "total_bathrooms": 3,
            "acres": 0.8,
            "listing_price": 289000,
            'listing_id': '1143578',
            "display_address": "123 Test St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78731"
        }

        pda().get_listing.return_value = fake_listing_data

        offer.pda_listing_uuid = pda_listing_uuid
        offer.save()

        self.assertEqual(offer.pda_listing_uuid, pda_listing_uuid)

        url = '/api/1.0.0/offer/{}/'.format(offer.id)

        data = {
            "application_id": offer.application.id,
            "offer_property_address": {
                "street": "2222 Test St.",
                "city": "Austin",
                "state": "TX",
                "zip": "78704"
            }
        }

        response = self.client.patch(url, data, **headers, format='json')
        json_response = response.json()

        offer = Offer.objects.get(id=json_response["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(offer.pda_listing_uuid, None)
        self.assertEqual(offer.year_built, None)
        self.assertEqual(offer.home_square_footage, None)
        self.assertEqual(offer.photo_url, None)
        self.assertEqual(offer.bedrooms, None)
        self.assertEqual(offer.bathrooms, None)
        self.assertEqual(offer.less_than_one_acre, None)
        self.assertEqual(offer.home_list_price, None)
        self.assertEqual(offer.mls_listing_id, None)
        self.assertEqual(offer.offer_property_address.street, "2222 Test St.")
        self.assertEqual(offer.offer_property_address.city, "Austin")
        self.assertEqual(offer.offer_property_address.state, "TX")
        self.assertEqual(offer.offer_property_address.zip, "78704")


    def test_will_not_update_an_offer_if_submitted_by_non_buying_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_user4")
            token = self.login_user(user)[1]
            headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }

            application = random_objects.random_application()
            application.save()
            
            offer = random_objects.random_offer(application=application)
            url = '/api/1.0.0/offer/{}/'.format(offer.id)

            data = {
                "year_built": "2020"
            }

            response = self.client.patch(url, data, **headers, format='json')
            json_response = response.json()
            self.assertEqual(response.status_code, 403)
            self.assertEqual(json_response['detail'], 'You do not have permission to perform this action.')

    def test_will_fail_gracefully_if_no_offer_exists(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_agent_user5")
            token = self.login_user(user)[1]
            headers = {
                    'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
            application = random_objects.random_application()
            application.buying_agent = agent
            application.save()
            url = '/api/1.0.0/offer/{}/'.format(11111111)

            data = {
                "year_built": "2020"
            }

            response = self.client.patch(url, data, **headers, format='json')

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"detail": "Not found."})

    def test_will_update_offer_address_if_nonexistant(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_agent_user3")
            token = self.login_user(user)[1]
            headers = {
                    'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
            application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
            application.buying_agent = agent
            application.save()

            offer = random_objects.random_offer(application=application)

            url = '/api/1.0.0/offer/{}/'.format(offer.id)

            data = {
                "year_built": "2020",
                "offer_property_address": {
                    "street": "1321 Test Rd.",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "78704"
                }
            }

            response = self.client.patch(url, data, **headers, format='json')
            self.assertEqual(response.status_code, 200)

    def test_get_one_offer(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_agent_user4")
            token = self.login_user(user)[1]
            headers = {
                    'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
            application = random_objects.random_application()
            application.buying_agent = agent
            application.save()

            offer = random_objects.random_offer(application=application)
            url = '/api/1.0.0/offer/{}/'.format(offer.id)

            response = self.client.get(url, **headers, format='json')
            json_response = response.json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(json_response['id'], str(offer.id))
            self.assertEqual(json_response['year_built'], offer.year_built)
            self.assertEqual(Application.objects.get(id=json_response['application_id']), offer.application)
            self.assertEqual(json_response['offer_property_address']['id'], str(offer.offer_property_address.id))

    def test_will_not_return_offer_if_user_is_not_buying_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("some_agent")
            token = self.login_user(user)[1]
            headers = {
                    'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
            application = random_objects.random_application()
            application.save()
            offer = random_objects.random_offer(application=application)
            url = '/api/1.0.0/offer/{}/'.format(offer.id)
            response = self.client.get(url, **headers, format='json')
            json_response = response.json()
            self.assertEqual(response.status_code, 403)
            self.assertEqual(json_response['detail'], 'You do not have permission to perform this action.')

    def test_will_return_status_not_found_if_offer_not_found(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_agent_user4")
            token = self.login_user(user)[1]
            headers = {
                    'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }
            agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
            application = random_objects.random_application()
            application.buying_agent = agent
            application.save()
            url = '/api/1.0.0/offer/{}/'.format('1111111')

            response = self.client.get(url, **headers, format='json')
            response.json()

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"detail": "Not found."})

    @mock.patch('user.models.requests.get')
    def test_will_return_bad_request_if_invalid_app_stage(self, user_mock):
        user_mock.return_value = data_generators.MockedAgentUserResponse()
        url = '/api/1.0.0/offer/'

        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE)
        application.buying_agent = self.agent
        application.save()

        request_data = {
                'year_built': 2012,
                'home_square_footage': 1300,
                'property_type': 'Single Family',
                'less_than_one_acre': True,
                'home_list_price': 500000,
                "offer_price": 510000,
                "contract_type": "Resale",
                "other_offers": "1-4",
                "offer_deadline": timezone.now(),
                "plan_to_lease_back_to_seller": "No",
                "waive_appraisal": False,
                "already_under_contract": True,
                "comments": "test comments",
                "application_id": application.id,
                "offer_property_address": {
                    "street": "2222 Test St.",
                    "city": "Austin",
                    "state": "TX",
                    "zip": 78704
                }
            }

        response = self.client.post(url, request_data, **self.headers, format='json')

        self.assertEqual(response.status_code, 400)

    @mock.patch('user.models.requests.get')
    def test_will_return_successful_create_if_offer_requested_app_stage(self, user_mock):
        user_mock.return_value = data_generators.MockedAgentUserResponse()
        url = '/api/1.0.0/offer/'

        offers = Offer.objects.all()
        offers_count = offers.count()

        application = random_objects.random_application(stage=ApplicationStage.OFFER_REQUESTED)
        application.buying_agent = self.agent
        application.save()

        request_data = {
            'year_built': 2012,
            'home_square_footage': 1300,
            'property_type': 'Single Family',
            'less_than_one_acre': True,
            'home_list_price': 500000,
            "offer_price": 510000,
            "contract_type": "Resale",
            "other_offers": "1-4",
            "offer_deadline": timezone.now(),
            "plan_to_lease_back_to_seller": "No",
            "waive_appraisal": 'No - undecided on covering delta & wants to know value first',
            "already_under_contract": True,
            "comments": "test comments",
            "application_id": application.id,
            "offer_property_address": {
                "street": "2222 Test St.",
                "city": "Austin",
                "state": "TX",
                "zip": 78704
            }
        }

        response = self.client.post(url, request_data, **self.headers, format='json')
        json_response = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(json_response["application_id"])
        self.assertEqual(json_response["property_type"], "Single Family")
        self.assertEqual(json_response["status"], "Incomplete")
        self.assertEqual(Offer.objects.all().count(), offers_count + 1)

    @mock.patch('user.models.requests.get')
    def test_will_return_successful_create_if_offer_submitted_app_stage(self, user_mock):
        user_mock.return_value = data_generators.MockedAgentUserResponse()
        url = '/api/1.0.0/offer/'

        offers = Offer.objects.all()
        offers_count = offers.count()

        application = random_objects.random_application(stage=ApplicationStage.OFFER_SUBMITTED)
        application.buying_agent = self.agent
        application.save()

        request_data = {
            'year_built': 2012,
            'home_square_footage': 1300,
            'property_type': 'Single Family',
            'less_than_one_acre': True,
            'home_list_price': 500000,
            "offer_price": 510000,
            "contract_type": "Resale",
            "other_offers": "1-4",
            "offer_deadline": timezone.now(),
            "plan_to_lease_back_to_seller": "No",
            "waive_appraisal": 'No - undecided on covering delta & wants to know value first',
            "already_under_contract": True,
            "comments": "test comments",
            "application_id": application.id,
            "offer_property_address": {
                "street": "2222 Test St.",
                "city": "Austin",
                "state": "TX",
                "zip": 78704
            }
        }

        response = self.client.post(url, request_data, **self.headers, format='json')
        json_response = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(json_response["property_type"], "Single Family")
        self.assertEqual(json_response["status"], "Incomplete")
        self.assertEqual(Offer.objects.all().count(), offers_count + 1)

    @patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
    def test_salesforce_bulk_endpoint(self, sf_mock):
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = random_objects.random_application(new_salesforce=str(fake.md5()))

        offer_payload = [{
            'Id': str(fake.md5()),
            Offer.STATUS_FIELD: fake.random_element(['Requested', 'EAV Complete', 'Approved',
                                                     'Backup Position Accepted', 'Denied', 'Won', 'Lost',
                                                     'Request Cancelled', 'Contract Cancelled']),
            Offer.YEAR_BUILT_FIELD: fake.year(),
            Offer.HOME_SQUARE_FOOTAGE_FIELD:fake.pyint(max_value=10000),
            Offer.PROPERTY_TYPE_FIELD: fake.random_element(list(PropertyType)),
            Offer.LESS_THAN_ONE_ACRE_FIELD: fake.random_element(['Yes', 'No']),
            Offer.HOME_LIST_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.OFFER_PRICE_FIELD: fake.random_int(min=200000, max=3000000),
            Offer.CONTRACT_TYPE_FIELD: fake.random_element(list(ContractType)),
            Offer.OTHER_OFFER_FIELD: fake.random_element(list(OtherOffers)),
            Offer.OFFER_DEADLINE_FIELD: fake.date_time_this_month(after_now=True, tzinfo=pytz.UTC),
            Offer.LEASE_BACK_TO_SELLER_FIELD: fake.random_element(list(PlanToLeaseBackToSeller)),
            Offer.WAIVE_APPRAISAL_FIELD: fake.random_element(list(WaiveAppraisal)),
            Offer.ALREADY_UNDER_CONTRACT_FIELD: fake.random_element(['Yes', 'No']),
            Offer.CUSTOMER_FIELD: application.new_salesforce,
            Offer.ADDRESS_STREET_FIELD: fake.street_address(),
            Offer.ADDRESS_CITY_FIELD: fake.city(),
            Offer.ADDRESS_STATE_FIELD: fake.state(),
            Offer.ADDRESS_ZIP_FIELD: fake.postcode(),
        }]

        url = '/api/1.0.0/offer/salesforce/bulk/'

        response = self.client.post(url, offer_payload, **headers, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(Offer.objects.first())
        offer = Offer.objects.first()
        self.assertIsNone(offer.offer_source)

        sf_mock.assert_called_once_with(offer.salesforce_id, {Offer.HOMEWARD_ID: str(offer.id)},
                                        Offer.salesforce_object_type)

    @mock.patch('user.models.requests.get')
    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_should_call_out_to_property_data_aggregator_with_pda_listing_uuid(self, pda, m):
        m.return_value = data_generators.MockedAgentUserResponse()

        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "id": pda_listing_uuid,
            "year_built": 1984,
            "square_feet": 1945,
            "acres": 2.3,
            "listing_price": 123456.78,
            'listing_id': '1106009',
            "display_address": "123 Main St.",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78731"
        }

        pda().get_listing.return_value = fake_listing_data

        url = '/api/1.0.0/offer/'

        request = {
            "application_id": self.application.id,
            "pda_listing_uuid": pda_listing_uuid
        }

        response = self.client.post(url, request, **self.headers, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json().get('pda_listing_uuid'), str(fake_listing_data['id']))
        self.assertEqual(response.json().get('mls_listing_id'), str(fake_listing_data['listing_id']))
        self.assertEqual(response.json().get('year_built'), fake_listing_data['year_built'])
        self.assertEqual(response.json().get('home_square_footage'), fake_listing_data['square_feet'])
        self.assertEqual(response.json().get('less_than_one_acre'), False)
        self.assertEqual(response.json().get('offer_property_address')['street'], fake_listing_data['display_address'])
        self.assertEqual(response.json().get('offer_property_address')['city'], fake_listing_data['city'])
        self.assertEqual(response.json().get('offer_property_address')['state'], fake_listing_data['state'])
        self.assertEqual(response.json().get('offer_property_address')['zip'], fake_listing_data['postal_code'])

    @mock.patch('application.generate_pdf_task.ProcessPdf.add_data_to_pdf')
    @mock.patch('user.models.requests.get')
    def test_returns_offer_contract_url(self, user_patch, pdf_mock):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        pdf_mock.return_value = 'www.blah.com'

        user = self.create_user("fake_agent_user4")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
        application = random_objects.random_application()
        application.buying_agent = agent
        application.save()

        offer = random_objects.random_offer(application=application)
        offer.contract_type = 'Resale'
        offer.property_type = 'Single Family'
        offer.save()
        offer.offer_property_address.state = 'TX'
        offer.offer_property_address.save()

        contract_template = ContractTemplate(filename='tx_resale_non_condo.pdf', contract_type=ContractType.RESALE, property_type=PropertyType.SINGLE_FAMILY, buying_state=BuyingState.TX, active=True)
        contract_template.save()

        url = '/api/1.0.0/offer/{}/contract/'.format(offer.id)

        response = self.client.get(url, **headers, format='json')
        json_response = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(json_response["url"])

    @mock.patch('application.generate_pdf_task.ProcessPdf.add_data_to_pdf')
    @mock.patch('user.models.requests.get')
    def test_does_not_return_offer_contract_url(self, user_patch, pdf_mock):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        pdf_mock.return_value = 'www.blah.com'

        user = self.create_user("fake_agent_user4")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
        application = random_objects.random_application()
        application.buying_agent = agent
        application.save()

        offer = random_objects.random_offer(application=application)
        offer.contract_type = 'Resale'
        offer.property_type = 'Condo'
        offer.save()
        offer.offer_property_address.state = 'TX'
        offer.offer_property_address.save()

        url = '/api/1.0.0/offer/{}/contract/'.format(offer.id)

        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, 404)

    @mock.patch('application.generate_pdf_task.ProcessPdf.add_data_to_pdf')
    @mock.patch('user.models.requests.get')
    def test_offer_not_found(self, user_patch, pdf_mock):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        pdf_mock.return_value = 'www.blah.com'

        user = self.create_user("fake_agent_user4")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
        application = random_objects.random_application()
        application.buying_agent = agent
        application.save()

        url = '/api/1.0.0/offer/{}/contract/'.format(uuid.uuid4())

        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, 404)

    @mock.patch('application.generate_pdf_task.ProcessPdf.add_data_to_pdf')
    @mock.patch('user.models.requests.get')
    def test_agent_not_attached_to_application(self, user_patch, pdf_mock):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        pdf_mock.return_value = 'www.blah.com'

        another_user = self.create_user("fake_agent_user2")
        another_token = self.login_user(another_user)[1]
        new_headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(another_token)
        }

        application = random_objects.random_application()
        application.buying_agent = random_objects.random_agent()
        application.save()

        offer = random_objects.random_offer(application=application)
        offer.contract_type = 'Resale'
        offer.property_type = 'Condo'
        offer.save()
        offer.offer_property_address.state = 'TX'
        offer.offer_property_address.save()

        url = '/api/1.0.0/offer/{}/contract/'.format(offer.id)

        response = self.client.get(url, **new_headers, format='json')

        self.assertEqual(response.status_code, 403)

    @mock.patch('user.models.requests.get')
    def test_start_date_return_for_offer(self, user_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        user = self.create_user("Real Estate Agent")
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                        product_offering=ProductOffering.BUY_SELL,
                                                        )
        application.buying_agent = agent
        application.save()
        offer = random_objects.random_offer(application=application)
        offer.save()

        headers = {'HTTP_AUTHORIZATION': f'Token {self.login_user(user)[1]}'}

        url = reverse_lazy('api:offer-closing-restricted-dates', kwargs={'pk': offer.pk})

        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, 200)
        fields_to_check_for = ['earliest_possible_close_date', 'latest_possible_close_date', 'restricted_close_dates']
        for item in fields_to_check_for:
            self.assertIn(item, response.json())
        end_time = datetime.fromisoformat(response.json()['latest_possible_close_date'])
        self.assertIsInstance(response.json()['restricted_close_dates'], list)
        # 18 months contain at least 546 days, but I'm paring 2 off
        days_gap = (end_time - datetime.now()).days
        self.assertGreater(days_gap, 544)

    @mock.patch('user.models.requests.get')
    def test_nonexistent_offer(self, user_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        user = self.create_user("Real Estate Agent")
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                        product_offering=ProductOffering.BUY_SELL,
                                                        )
        application.buying_agent = agent
        application.save()

        headers = {'HTTP_AUTHORIZATION': f'Token {self.login_user(user)[1]}'}

        non_existent_offer = uuid.uuid4()

        url = reverse_lazy('api:offer-closing-restricted-dates', kwargs={'pk': non_existent_offer})

        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, 404)

    @mock.patch('user.models.requests.get')
    def test_offer_creation_validation_fails_when_preferred_closing_date_too_early(self, user_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        product_offering = self.application.product_offering
        earliest_closing_date = date_restrictor.get_earliest_close_date(product_offering, datetime.now())
        invalid_preferred_closing_date = (earliest_closing_date - timedelta(days=1)).isoformat()
        self.request_data['preferred_closing_date'] = invalid_preferred_closing_date

        response = self.client.post('/api/1.0.0/offer/', self.request_data, **self.headers, format='json')

        self.assertEqual(response.status_code, 400, 'Validation should have caught a preferred closing date that was too early.')
        validation_error = response.json()['preferred_closing_date'][0]
        self.assertEqual(validation_error, f'preferred closing date of {invalid_preferred_closing_date} cannot be before {earliest_closing_date.isoformat()}',
            'Validation error was not correct.')

    @mock.patch('user.models.requests.get')
    def test_offer_update_validation_fails_when_preferred_closing_date_too_early(self, user_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION, product_offering=ProductOffering.BUY_SELL)
        application.buying_agent = self.agent
        application.save()

        offer = random_objects.random_offer(application=application)

        created_at_date = offer.created_at
        product_offering = application.product_offering
        earliest_closing_date = date_restrictor.get_earliest_close_date(product_offering, created_at_date)
        invalid_preferred_closing_date = (earliest_closing_date - timedelta(days=1)).isoformat()

        url = '/api/1.0.0/offer/{}/'.format(offer.id)
        data = { "preferred_closing_date": invalid_preferred_closing_date }
        response = self.client.patch(url, data, **self.headers, format='json')

        self.assertIsNotNone(created_at_date, 'Created at date was not present in already created offer.')
        self.assertEqual(response.status_code, 400, 'Validation should have caught a preferred closing date that was too early.')
        validation_error = response.json()['preferred_closing_date'][0]
        self.assertEqual(validation_error, f'preferred closing date of {invalid_preferred_closing_date} cannot be before {earliest_closing_date.isoformat()}',
            'Validation error was not correct.')

    @mock.patch('user.models.requests.get')
    def test_offer_creation_validation_fails_when_preferred_closing_date_too_late(self, user_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        latest_closing_date = date_restrictor.get_latest_close_date(datetime.now())
        invalid_preferred_closing_date = (latest_closing_date + timedelta(days=1)).isoformat()
        self.request_data['preferred_closing_date'] = invalid_preferred_closing_date

        response = self.client.post('/api/1.0.0/offer/', self.request_data, **self.headers, format='json')

        self.assertEqual(response.status_code, 400, f'Validation should have caught a preferred closing date that was too late.')
        validation_error = response.json()['preferred_closing_date'][0]
        self.assertEqual(validation_error, f'preferred closing date of {invalid_preferred_closing_date} cannot be after {latest_closing_date.isoformat()}',
            'Validation error was not correct.')

    @mock.patch('user.models.requests.get')
    def test_offer_update_validation_fails_when_preferred_closing_date_too_late(self, user_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION, product_offering=ProductOffering.BUY_SELL)
        application.buying_agent = self.agent
        application.save()

        offer = random_objects.random_offer(application=application)

        created_at_date = offer.created_at
        latest_closing_date = date_restrictor.get_latest_close_date(created_at_date)
        invalid_preferred_closing_date = (latest_closing_date + timedelta(days=1)).isoformat()

        url = '/api/1.0.0/offer/{}/'.format(offer.id)
        data = { "preferred_closing_date": invalid_preferred_closing_date }
        response = self.client.patch(url, data, **self.headers, format='json')

        self.assertIsNotNone(created_at_date, 'Created at date was not present in already created offer.')
        self.assertEqual(response.status_code, 400, 'Validation should have caught a preferred closing date that was too late.')
        validation_error = response.json()['preferred_closing_date'][0]
        self.assertEqual(validation_error, f'preferred closing date of {invalid_preferred_closing_date} cannot be after {latest_closing_date.isoformat()}',
            'Validation error was not correct.')

    @mock.patch('utils.date_restrictor.calculate_dates_at_capacity')
    @mock.patch('user.models.requests.get')
    def test_offer_creation_validation_fails_when_preferred_closing_date_restricted(self, user_patch, date_restrictor_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        invalid_preferred_closing_date = (datetime.now() + relativedelta(months=1, weekday=SA(+4))).date()
        date_restrictor_patch.return_value = [invalid_preferred_closing_date]
        self.request_data['preferred_closing_date'] = invalid_preferred_closing_date.isoformat()

        response = self.client.post('/api/1.0.0/offer/', self.request_data, **self.headers, format='json')

        self.assertEqual(response.status_code, 400, f'Validation should have caught a preferred closing date that was restricted.')
        validation_error = response.json()['preferred_closing_date'][0]
        self.assertEqual(validation_error, f'preferred closing date of {invalid_preferred_closing_date.isoformat()} cannot be on a restricted date',
            'Validation error was not correct.')

    @mock.patch('utils.date_restrictor.calculate_dates_at_capacity')
    @mock.patch('user.models.requests.get')
    def test_offer_update_validation_fails_when_preferred_closing_date_restricted(self, user_patch, date_restrictor_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION, product_offering=ProductOffering.BUY_SELL)
        application.buying_agent = self.agent
        application.save()

        offer = random_objects.random_offer(application=application)

        created_at_date = offer.created_at
        product_offering = application.product_offering
        invalid_preferred_closing_date = date_restrictor.get_earliest_close_date(product_offering, created_at_date)
        date_restrictor_patch.return_value = [invalid_preferred_closing_date]

        url = '/api/1.0.0/offer/{}/'.format(offer.id)
        data = { "preferred_closing_date": invalid_preferred_closing_date.isoformat() }
        response = self.client.patch(url, data, **self.headers, format='json')

        self.assertIsNotNone(created_at_date, 'Created at date was not present in already created offer.')
        self.assertEqual(response.status_code, 400, f'Validation should have caught a preferred closing date that was restricted.')
        validation_error = response.json()['preferred_closing_date'][0]
        self.assertEqual(validation_error, f'preferred closing date of {invalid_preferred_closing_date.isoformat()} cannot be on a restricted date',
            'Validation error was not correct.')

    @mock.patch('utils.date_restrictor.calculate_dates_at_capacity')
    @mock.patch('user.models.requests.get')
    def test_offer_creation_validation_succeeds_when_preferred_closing_date_ok(self, user_patch, date_restrictor_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        valid_preferred_closing_date = (datetime.now() + relativedelta(months=1, weekday=MO(+4))).date()
        date_restrictor_patch.return_value = []
        self.request_data['preferred_closing_date'] = valid_preferred_closing_date.isoformat()

        response = self.client.post('/api/1.0.0/offer/', self.request_data, **self.headers, format='json')

        self.assertEqual(response.status_code, 201, f'Validation of preferred closing date should have succeeded.')

    @mock.patch('utils.date_restrictor.calculate_dates_at_capacity')
    @mock.patch('user.models.requests.get')
    def test_offer_update_validation_succeeds_when_preferred_closing_date_ok(self, user_patch, date_restrictor_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                        product_offering=ProductOffering.BUY_SELL)
        application.buying_agent = self.agent
        application.save()

        offer = random_objects.random_offer(application=application)

        valid_preferred_closing_date = (offer.created_at + relativedelta(months=1, weekday=MO(+4))).date()
        date_restrictor_patch.return_value = []

        url = '/api/1.0.0/offer/{}/'.format(offer.id)
        data = { "preferred_closing_date": valid_preferred_closing_date }
        response = self.client.patch(url, data, **self.headers, format='json')

        self.assertEqual(response.status_code, 200, f'Validation of preferred closing date should have succeeded, but '
                                                    f'failed with the following error - {response.json()}')

    @mock.patch('api.v1_0_0.serializers.offer_serializer.OfferSerializer.validate_preferred_closing_date_restrictions')
    @mock.patch('user.models.requests.get')
    def test_offer_preferred_closing_date_validation_skipped_if_field_does_not_exist(self, user_patch, validation_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()
        validation_patch.return_value = None
        self.request_data['preferred_closing_date'] = None

        self.assertFalse(validation_patch.called, 'Preferred closing date validation should not have been called on an empty field.')

    @mock.patch('api.v1_0_0.serializers.offer_serializer.OfferSerializer.validate_preferred_closing_date_restrictions')
    @mock.patch('user.models.requests.get')
    def test_offer_update_preferred_closing_date_validation_skipped_if_value_unchanged(self, user_patch, validation_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()
        validation_patch.return_value = None

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION, product_offering=ProductOffering.BUY_SELL)
        application.buying_agent = self.agent
        application.save()

        preferred_closing_date = date(2020, 12, 7).isoformat()
        offer = random_objects.random_offer(application=application, preferred_closing_date=preferred_closing_date)

        url = '/api/1.0.0/offer/{}/'.format(offer.id)
        data = { "preferred_closing_date": preferred_closing_date }
        response = self.client.patch(url, data, **self.headers, format='json')

        self.assertFalse(validation_patch.called, 'Preferred closing date validation should not have been called on unchanged field.')
        self.assertEqual(response.status_code, 200, f'Validation of preferred closing date should have succeeded.')

    @mock.patch('api.v1_0_0.serializers.offer_serializer.OfferSerializer.validate_preferred_closing_date_restrictions')
    @mock.patch('user.models.requests.get')
    def test_offer_update_preferred_closing_date_validation_called_if_value_changed(self, user_patch, validation_patch):
        user_patch.return_value = data_generators.MockedAgentUserResponse()
        validation_patch.return_value = None

        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION, product_offering=ProductOffering.BUY_SELL)
        application.buying_agent = self.agent
        application.save()

        initial_preferred_closing_date = date(2020, 12, 7).isoformat()
        offer = random_objects.random_offer(application=application, preferred_closing_date=initial_preferred_closing_date)
        updated_preferred_closing_date = date(2020, 12, 8).isoformat()

        url = '/api/1.0.0/offer/{}/'.format(offer.id)
        data = { "preferred_closing_date": updated_preferred_closing_date }
        self.client.patch(url, data, **self.headers, format='json')

        self.assertTrue(validation_patch.called, 'Preferred closing date validation should have been called on a changed field.')

    @mock.patch('user.models.requests.get')
    def test_general_restricted_calendar(self, user_patch):
        url = reverse_lazy('api:offer-internal-closing-restricted-dates')

        date_at_capacity = date.today() + timedelta(days=1)
        for _ in range(MAXIMUM_CLOSING_CAPACITY + 1):
            app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.WON)

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIsoFormattedDate(response.json()['earliest_possible_close_date'])
        self.assertIsoFormattedDate(response.json()['latest_possible_close_date'])
        self.assertIn(date_at_capacity.isoformat(), response.json()['restricted_close_dates'])
        self.assertIn(date(datetime.today().year, 12, 25).isoformat(),
                      response.json()['restricted_close_dates'])
        self.assertEqual(date_at_capacity, parser.parse(response.json()['restricted_close_dates'][0]).date())
