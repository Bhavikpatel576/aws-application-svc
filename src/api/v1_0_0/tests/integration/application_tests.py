"""
Application app test cases.
"""
import datetime
import json
import os
from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from api.v1_0_0.tests._utils.data_generators import get_fake_address
from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import Application, HomeBuyingStage, ProductOffering
from application.models.customer import Customer
from application.models.models import (Note, NoteType, ApplicationStage, StageHistory, Address)
from application.models.mortgage_lender import MortgageLender
from application.models.real_estate_agent import RealEstateAgent
from application.models.internal_support_user import InternalSupportUser
from application.tests import random_objects
from application.tests.random_objects import fake, random_new_home_purchase, \
    random_current_home, random_preapproval, random_internal_support_user


def raise_exception(*args, **kwargs):
    raise Exception('Invalid data.')


class ApplicationTests(AuthMixin, APITestCase):
    def setUp(self):
        self.sf_patch = patch("application.tasks.push_to_salesforce")
        self.hubspot_patch = patch("utils.hubspot.send_mail")
        self.pbc_patch = patch("utils.partner_branding_config_service.get_partner")
        self.sf_patch.start()
        self.hubspot_patch.start()
        self.addCleanup(self.sf_patch.stop)
        self.addCleanup(self.hubspot_patch.stop)

    def test_list_without_login(self):
        """
        Test listing API without login.
        """
        url = '/api/1.0.0/application/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_with_login(self):
        """
        Test list API with login.
        """
        token = self.create_and_login_admin('fakeloginadmin')
        url = '/api/1.0.0/application/'
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_filter_with_valid_data(self):  # noqa: C901
        """
        Test list filters using valid data.
        """
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplicant')
        application_id = str(application.id)
        listing_base_url = '/api/1.0.0/application/'
        response = self.client.get(listing_base_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        record_count = response.json()['count']
        # Application list API with filter.
        # If only Z-A filter applied,number of records in listing does not
        # decrease. It is same as total number of records without any filter.

        # ------- ordering on column 'stage' ---------------
        filter_data = 'ordering={0}'.format('stage')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-stage')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'stage={}'.format(application.stage)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.stage, record['stage'])
        filter_data = 'stage={}'.format('draft')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)

        # self.assertEqual(response.json()['count'], 0)
        for record in response.json()['results']:
            self.assertNotEqual(application.stage, record['stage'])

        # ------- ordering on column 'lead status' ---------------
        filter_data = 'lead_status={}'.format(application.lead_status)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.lead_status, record['lead_status'])
        filter_data = 'stage={}'.format('Qualifying')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)

        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'name' ---------------

        filter_data = 'ordering={0}'.format('customer__name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-customer__name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'name={}'.format(application.customer.name)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.customer.name,
                             record['customer']['name'])
        filter_data = 'name={}'.format('randon_name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'email' ---------------
        filter_data = 'ordering={0}'.format('customer__email')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-customer__email')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'email={}'.format(application.customer.email)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.customer.email,
                             record['customer']['email'])
        filter_data = 'email={}'.format('randon_email@something.com')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'phone' ---------------
        filter_data = 'ordering={0}'.format('customer__phone')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('customer__phone')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'phone={}'.format(application.customer.phone)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.customer.phone,
                             record['customer']['phone'])
        filter_data = 'phone={}'.format('2-111-111-1111')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'start_date' ---------------
        filter_data = 'ordering={0}'.format('start_date')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-start_date')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'start_date={}'.format('1970-01-01')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)
        filter_data = 'start_date={}'.format(
            {"from_date": "1970-01-01", "to_date": "1970-12-01"})
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'agents_name' ---------------
        filter_data = 'ordering={0}'.format('real_estate_agent__name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-real_estate_agent__name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'agents_name={}'.format(
            application.real_estate_agent.name)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.real_estate_agent.name,
                             record['real_estate_agent']['name'])
        filter_data = 'agents_name={}'.format('random Agent')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'agents_phone' ---------------
        filter_data = 'ordering={0}'.format('real_estate_agent__phone')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-real_estate_agent__phone')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'agents_phone={}'.format(
            application.real_estate_agent.phone)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.real_estate_agent.phone,
                             record['real_estate_agent']['phone'])
        filter_data = 'agents_phone={}'.format('3-000-000-0000')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'home buying stage' ---------------
        filter_data = 'ordering={0}'.format('home_buying_stage')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-home_buying_stage')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'home_buying_stage={}'.format(
            application.home_buying_stage)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.home_buying_stage,
                             record['home_buying_stage'])
        filter_data = 'home_buying_stage={}'.format('working with a builder')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'agents_email' ---------------
        filter_data = 'ordering={0}'.format('real_estate_agent__email')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-real_estate_agent__email')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'agents_email={}'.format(
            application.real_estate_agent.email)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.real_estate_agent.email,
                             record['real_estate_agent']['email'])
        filter_data = 'agents_email={}'.format('random_agent@something.com')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'builder_name' ---------------
        filter_data = 'ordering={0}'.format('builder__company_name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-builder__company_name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'builder__company_name={}'.format(application.builder.company_name)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.builder.company_name,
                             record['builder']['company_name'])
        filter_data = 'builder__company_name={}'.format('randon builder name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'shopping_location' ---------------
        filter_data = 'ordering={0}'.format('shopping_location')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-shopping_location')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'shopping_location={}'.format(
            application.shopping_location)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.shopping_location,
                             record['shopping_location'])
        filter_data = 'shopping_location={}'.format('Pune, India')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'mortgage_lender_name' ---------------
        filter_data = 'ordering={0}'.format('mortgage_lender__name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-mortgage_lender__name')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'lender_name={}'.format(application.mortgage_lender.name)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.mortgage_lender.name,
                             record['mortgage_lender']['name'])
        filter_data = 'lender_name={}'.format('Random Lender')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'mortgage_lender_email' ---------------
        filter_data = 'ordering={0}'.format('mortgage_lender__email')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-mortgage_lender__email')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'lender_email={}'.format(
            application.mortgage_lender.email)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.mortgage_lender.email,
                             record['mortgage_lender']['email'])
        filter_data = 'lender_email={}'.format('agent@something.com')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'mortgage_lender_phone' ---------------
        filter_data = 'ordering={0}'.format('mortgage_lender__phone')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-mortgage_lender__phone')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'lender_phone={}'.format(
            application.mortgage_lender.phone)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.mortgage_lender.phone,
                             record['mortgage_lender']['phone'])
        filter_data = 'lender_phone={}'.format('4-000-000-0000')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'max_price' ---------------
        filter_data = 'ordering={0}'.format('max_price')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-max_price')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'max_price={}'.format(application.max_price)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.max_price, float(record['max_price']))
        filter_data = 'max_price={}'.format('100000000000000000')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'min_price' ---------------
        filter_data = 'ordering={0}'.format('min_price')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-min_price')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'min_price={}'.format(application.min_price)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.min_price, float(record['min_price']))
        filter_data = 'min_price={}'.format('100000000000000000')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'move_in' ---------------
        filter_data = 'ordering={0}'.format('move_in')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-move_in')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'move_in={}'.format(application.move_in)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(application.move_in, record['move_in'])
        filter_data = 'move_in={}'.format('18-24months')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'id' ---------------
        filter_data = 'ordering={0}'.format('id')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-id')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'id={}'.format(application.id)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(str(application.id), record['id'])
        filter_data = 'id={}'.format('RANDOM-UUID-123-ADS')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ------- ordering on column 'move_by_date' ---------------
        filter_data = 'ordering={0}'.format('move_by_date')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-move_by_date')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'move_by_date={}'.format(application.move_by_date.date())
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        for record in response.json()['results']:
            self.assertEqual(
                str(application.move_by_date.date()), record['move_by_date'])
        filter_data = 'move_by_date={}'.format('1970-01-01')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.json()['count'], 0)

        # ---------- ordering on column 'builder__address' -------------
        filter_data = 'ordering={0}'.format('builder__address__street')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-builder__address__street')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'builder__address={}'.format(
            application.builder.address.street)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.json()['count'], 0)
        for record in response.json()['results']:
            if not (application.builder.address.street in record['builder']['address']['street']
                    or application.builder.address.street in record['builder']['address']['city']
                    or application.builder.address.street in record['builder']['address']['state']
                    or application.builder.address.street in record['builder']['address']['zip']):
                self.assertRaises(ValueError, raise_exception,
                                  'Invalid value error.')

        # ---------- ordering on column 'offer_property_address' -------------
        filter_data = 'ordering={0}'.format('offer_property_address__street')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-offer_property_address__street')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'offer_property_address={}'.format(
            application.offer_property_address.street)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.json()['count'], 0)
        for record in response.json()['results']:
            if not (application.offer_property_address.street in record['offer_property_address']['street']
                    or application.offer_property_address.street in record['offer_property_address']['city']
                    or application.offer_property_address.street in record['offer_property_address']['state']
                    or application.offer_property_address.street in record['offer_property_address']['zip']):
                self.assertRaises(ValueError, raise_exception,
                                  'Invalid value error.')

        # ---------- ordering on column 'current_home__address' -------------
        filter_data = 'ordering={0}'.format('current_home__address__street')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)
        filter_data = 'ordering={0}'.format('-current_home__address__street')
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], record_count)

        filter_data = 'current_home__address={}'.format(
            application.current_home.address.street)
        url = '{}?{}'.format(listing_base_url, filter_data)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.json()['count'], 0)
        for record in response.json()['results']:
            if not (application.current_home.address.street in record['current_home']['address']['street']
                    or application.current_home.address.street in record['current_home']['address']['city']
                    or application.current_home.address.street in record['current_home']['address']['state']
                    or application.current_home.address.street in record['current_home']['address']['zip']):
                self.assertRaises(ValueError, raise_exception,
                                  'Invalid value error.')
        # Application detail view with filter.
        filter_data = 'name=' + application.customer.name + '&email=' + application.customer.email + '&phone=' + \
            application.customer.phone + '&stage=' + application.stage + \
            '&start_date=' + str(application.start_date).split(' ')[0]
        url = '/api/1.0.0/application/' + application_id + '/?' + filter_data
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_filter_with_invalid_data(self):
        """
        Test list filters using invalid data.
        """
        application_id = str(self.create_application('fakeapplicant').id)
        filter_data = 'name=abc&email=abc&phone=abc&stage=abc&start_date=2011-01-01'
        url = '/api/1.0.0/application/' + application_id + '/?' + filter_data
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_application_get_with_login(self):
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['current_home']['images']), 0)

    def test_application_get_without_login(self):
        """
        Test application get without login.
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_application_get_with_unrelated_user(self):
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_users_application_no_cx(self):
        user = self.create_user('fakeapplicant')
        customer = Customer.objects.create(name=fake.name(), email=user.email, phone=fake.phone_number())
        app = Application.objects.create(customer=customer)
        url = '/api/1.0.0/user/application/active/'
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.data.get('cx_manager'), None)
        self.assertEqual(response.data.get('loan_advisor'), None)

    @patch("application.signals.get_partner")
    def test_get_users_application(self, get_partner_patch):
        user = self.create_user('fakeapplicant')
        get_partner_patch.return_value = {}
        customer = Customer.objects.create(name=fake.name(), email=user.email, phone=fake.phone_number())
        cx_manager = random_internal_support_user(sf_id="some-sf-id-a")
        loan_advisor = random_internal_support_user(sf_id="some-sf-id-b")
        current_home = random_current_home(floor_price=random_objects.random_floor_price(), anything_needs_repairs=True, made_repairs_or_updates=True)
        app = Application.objects.create(customer=customer, stage=ApplicationStage.INCOMPLETE,
                                         current_home=current_home,
                                         new_home_purchase=random_new_home_purchase(
                                         customer_purchase_close_date=fake.date_this_month(after_today=True)),
                                         preapproval=random_preapproval(), cx_manager=cx_manager, loan_advisor=loan_advisor,
                                         product_offering=ProductOffering.BUY_ONLY, apex_partner_slug='some-slug', needs_lender=True)

        url = '/api/1.0.0/user/application/active/'
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stage'], ApplicationStage.INCOMPLETE)
        response_current_home_address = response.data['current_home']['address']
        self.assertEqual(response_current_home_address['city'], current_home.address.city)
        self.assertEqual(response_current_home_address['street'], current_home.address.street)
        self.assertEqual(response.data['current_home']['anything_needs_repairs'], True)
        self.assertEqual(response.data['current_home']['made_repairs_or_updates'], True)

        self.assertEqual(response.data.get('stage'), ApplicationStage.INCOMPLETE)

        self.assertEqual(response.data.get('new_home_purchase').get('option_period_end_date'),
                         app.new_home_purchase.option_period_end_date.isoformat())
        self.assertEqual(response.data.get('new_home_purchase').get('homeward_purchase_close_date'),
                         app.new_home_purchase.homeward_purchase_close_date.isoformat())
        self.assertEqual(response.data.get('new_home_purchase').get('homeward_purchase_status'),
                         app.new_home_purchase.homeward_purchase_status)
        self.assertEqual(response.data.get('new_home_purchase').get('customer_purchase_close_date'),
                         app.new_home_purchase.customer_purchase_close_date.isoformat())
        self.assertAlmostEqual(Decimal(response.data.get('new_home_purchase').get('contract_price')),
                               app.new_home_purchase.contract_price)
        self.assertAlmostEqual(Decimal(response.data.get('new_home_purchase').get('earnest_deposit_percentage')),
                         app.new_home_purchase.earnest_deposit_percentage)
        self.assertEqual(response.data.get('new_home_purchase').get('is_reassigned_contract'),
                               app.new_home_purchase.is_reassigned_contract)

        self.assertEqual(response.data.get('new_home_purchase').get('address').get('street'),
                         app.new_home_purchase.address.street)
        self.assertEqual(response.data.get('new_home_purchase').get('address').get('city'),
                         app.new_home_purchase.address.city)
        self.assertEqual(response.data.get('new_home_purchase').get('address').get('state'),
                         app.new_home_purchase.address.state)
        self.assertEqual(response.data.get('new_home_purchase').get('address').get('zip'),
                         app.new_home_purchase.address.zip)

        self.assertAlmostEqual(Decimal(response.data.get('new_home_purchase').get('rent')
                                       .get('amount_months_one_and_two')),
                         app.new_home_purchase.rent.amount_months_one_and_two)
        self.assertAlmostEqual(Decimal(response.data.get('new_home_purchase').get('rent')
                                       .get('daily_rental_rate')),
                               app.new_home_purchase.rent.daily_rental_rate)
        self.assertEqual(response.data.get('new_home_purchase').get('rent').get('type'),
                         app.new_home_purchase.rent.type)


        self.assertEqual(Decimal(response.data.get('preapproval').get('amount')), app.preapproval.amount)
        self.assertEqual(response.data.get('preapproval').get('vpal_approval_date'),
                         app.preapproval.vpal_approval_date.isoformat())
        self.assertEqual(Decimal(response.data.get('preapproval').get('estimated_down_payment')),
                         app.preapproval.estimated_down_payment)

        self.assertEqual(response.data.get('current_home').get('floor_price').get('type'),
                         current_home.floor_price.type)
        self.assertEqual(Decimal(response.data.get('current_home').get('floor_price').get('amount')),
                         current_home.floor_price.amount)
        self.assertEqual(Decimal(response.data.get('current_home').get('floor_price').get('preliminary_amount')),
                         current_home.floor_price.preliminary_amount)
        self.assertEqual(response.data.get('product_offering'), ProductOffering.BUY_ONLY.value)
        self.assertEqual(response.data.get("cx_manager").get("email"), cx_manager.email)
        self.assertEqual(response.data.get("loan_advisor").get("email"), loan_advisor.email)
        self.assertEqual(response.data.get("mortgage_status"), app.mortgage_status)
        self.assertEqual(response.data.get("apex_partner_slug"), app.apex_partner_slug)
        self.assertEqual(response.data.get("needs_lender"), app.needs_lender)

    def test_application_get_with_invalid_id(self):
        """
        Test application get with invalid id
        """
        application_id = '12345'
        url = '/api/1.0.0/application/' + application_id + '/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_application_patch_with_valid_data(self):
        """
        Test application patch for valid data.
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        customer_data = {"name": "fakeCustName", "phone": "1-222-229-2222"}
        address_data = {"zip": "12345"}
        current_home_data = {"market_value": 120, 'address': address_data}
        offer_property_address_data = {"zip": "123"}
        agents_data = {
            'name': 'updated name',
            'email': 'updateagent@gmail.com',
            'phone': '1-001-222-2222',
            'company': 'Updated Company'
        }
        application_data = {"customer": customer_data, 'current_home': current_home_data,
                            'offer_property_address': offer_property_address_data, 'real_estate_agent': agents_data}
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, application_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer']
                         ['name'], customer_data['name'])
        self.assertEqual(response.data['current_home']
                         ['address']['zip'], address_data['zip'])

    def test_application_patch_with_user(self):
        """
        Test application patch for valid data.
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        customer_data = {"name": "fakeCustName", "phone": "1-222-229-2222"}
        address_data = {"zip": "12345"}
        current_home_data = {"market_value": 120, 'address': address_data}
        offer_property_address_data = {"zip": "123"}
        agents_data = {
            'name': 'updated name',
            'email': 'updateagent@gmail.com',
            'phone': '1-001-222-2222',
            'company': 'Updated Company'
        }
        application_data = {"customer": customer_data, 'current_home': current_home_data,
                            'offer_property_address': offer_property_address_data, 'real_estate_agent': agents_data}
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, application_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_application_patch_with_invalid_data(self):
        """
        Test application patch for invalid data
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        customer_invalid_data = {"phone": "123-123-12", "email": "test"}
        application_invalid_data = {
            "customer": customer_invalid_data, "offer_property_address": "invalid_address"}
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, application_invalid_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        customer_invalid_data = {
            "phone": "12-123-123-12", "email": "test@gmail.com"}
        offer_property_address_data = {
            'city': 'Test City'
        }
        application_invalid_data = {"customer": customer_invalid_data,
                                    "offer_property_address": offer_property_address_data}
        response = self.client.patch(url, application_invalid_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_application_patch_without_login(self):
        """
        Test application patch without login
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        customer_data = {"name": "fakeCustName"}
        application_data = {"customer": customer_data}
        response = self.client.patch(url, application_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_application_patch_with_invalid_id(self):
        """
        Test application patch with invalid id
        """
        invalid_id = '12345'
        url = '/api/1.0.0/application/' + invalid_id + '/'
        customer_data = {"name": "fakeCustName"}
        application_data = {"customer": customer_data}
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, application_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_application_post(self):
        """
        Test application for post method
        """
        url = '/api/1.0.0/application/'
        customer_data = {"name": "fakeCustName"}
        application_data = {"customer": customer_data}
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, application_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_application_post_with_user(self):
        """
        Test application for post method
        """
        url = '/api/1.0.0/application/'
        customer_data = {"name": "fakeCustName"}
        application_data = {"customer": customer_data}
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, application_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_application_delete(self):
        """
        Test application for delete method
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_application_delete_with_user(self):
        """
        Test application for delete method
        """
        application_id = str(self.create_application('fakeapplicant').id)
        url = '/api/1.0.0/application/' + application_id + '/'
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_application_stage_change_without_comment(self):
        """
        Test if note is generated on stage change without comment.
        """
        application_id = self.create_application('fakeapplicant').id
        url = '/api/1.0.0/application/{}/'.format(application_id)
        token = self.create_and_login_admin('fakeloginadmin')
        data = {
            "stage": ApplicationStage.FLOOR_PRICE_REQUESTED
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.patch(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_application_stage_change_with_comment(self):
        """
        Test if note is generated on stage change with comment.
        """
        application_id = self.create_application('fakeapplicant').id
        url = '/api/1.0.0/application/{}/'.format(application_id)
        token = self.create_and_login_admin('fakeloginadmin')
        data = {
            "stage": ApplicationStage.FLOOR_PRICE_REQUESTED.value,
            "comment": "<p>Test Comment</p>"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.patch(url, data, **headers)
        title = "{} to {}".format(
            ApplicationStage.COMPLETE.value, ApplicationStage.FLOOR_PRICE_REQUESTED.value)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note = Note.objects.filter(
            application_id=application_id, type=NoteType.APPLICATION_STAGE)
        self.assertEqual(note[0].title, title)

    def test_application_stage_change_by_user(self):
        application_id = self.create_application('fakeapplicant').id
        url = '/api/1.0.0/application/{}/'.format(application_id)
        token = self.create_and_login_user('fakeloginuser')
        data = {
            "stage": ApplicationStage.FLOOR_PRICE_REQUESTED.value,
            "comment": "<p>Test Comment</p>"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.patch(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_application_task_status_for_admin_with_no_application(self):
        """
        test if api provide result for authenticated admin with no application
        """
        url = '/api/1.0.0/application/task-status/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_application_task_status_for_user_with_no_application(self):
        """
        test if api provide result for authenticated user with no application
        """
        url = '/api/1.0.0/application/task-status/'
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("utils.salesforce.homeward_salesforce.get_user_by_id")
    @patch("utils.salesforce.homeward_salesforce.get_account_by_id")
    def test_should_update_record_from_salesforce(self, sf_account_mock, sf_user_mock):
        sf_account_mock.return_value = {
            Customer.FIRST_NAME_FIELD: 'Sydne',
            Customer.LAST_NAME_FIELD: 'Kleespies',
            Customer.PHONE_FIELD: '2222222222',
            Customer.EMAIL_FIELD: 'sydne@homeward.com',
            RealEstateAgent.BUYING_AGENT_COMPANY_FIELD: 'Kleespies Group'
        }

        sf_user_mock.return_value = {
            InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
            InternalSupportUser.USER_BIO: "Some BIO...",
            InternalSupportUser.USER_FIRST_NAME: "Test",
            InternalSupportUser.USER_LAST_NAME: "CX",
            InternalSupportUser.USER_PHONE: "1111111111",
            InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
            InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
            InternalSupportUser.USER_PROFILE_NAME: "CXA",
            InternalSupportUser.ID_FIELD: "0054P00000AStdhQAD"
        }

        customer = Customer.objects.create(name='Brandon Kirchner', email='brandon@homeward.com', phone='512-923-5534')
        current_home = self.create_currenthome('sf')
        agent = RealEstateAgent.objects.create(name='Ronald Realtor', phone='777-777-7777', email='ronald@realor.com',
                                               company='Real Estate Business')
        existing_cx_manager = random_internal_support_user(sf_id="0054P00000AStdhQAD")
        lender = MortgageLender.objects.create(name='Larry Lender', email='larry@lender.com', phone='999-999-9999')
        offer_property_address = Address.objects.create(**get_fake_address('test'))
        Application.objects.create(customer=customer, lead_source='blah', lead_source_drill_down_1='boop',
                                   stage=ApplicationStage.INCOMPLETE, current_home=current_home,
                                   min_price=150000, max_price=350000, move_in='0-3 months',
                                   shopping_location='Portland, Oregon USA', real_estate_agent=agent,
                                   mortgage_lender=lender, self_reported_referral_source='news_article',
                                   self_reported_referral_source_detail='colin told me',
                                   home_buying_stage=HomeBuyingStage.MAKING_OFFERS, internal_referral='blah',
                                   offer_property_address=offer_property_address, cx_manager=existing_cx_manager)

        module_dir = os.path.dirname(__file__)
        data = open(os.path.join(module_dir, '../static/sf_record.json')).read()
        url = '/api/1.0.0/application/salesforce/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, json.loads(data), **headers, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_application = Application.objects.filter(customer__email=customer.email).first()

        self.assertEqual(updated_application.move_in, '3-6 months')
        self.assertEqual(updated_application.min_price, 250000)
        self.assertEqual(updated_application.max_price, 450000)
        self.assertEqual(updated_application.self_reported_referral_source, 'news_article')
        self.assertEqual(updated_application.self_reported_referral_source_detail, 'telephone')
        self.assertEqual(updated_application.home_buying_stage, 'Making an offer')
        self.assertEqual(updated_application.lead_source, 'Direct')
        self.assertEqual(updated_application.lead_source_drill_down_1, 'Apple')
        self.assertEqual(updated_application.lead_status, 'Qualified')
        self.assertEqual(updated_application.stage, 'complete')
        self.assertEqual(updated_application.internal_referral, 'blahblah')

        self.assertEqual(updated_application.builder.representative_name, 'Brian Builder')
        self.assertEqual(updated_application.builder.company_name, 'MHI')
        self.assertEqual(updated_application.builder.representative_email, "brian@builder.com")
        self.assertEqual(updated_application.builder.representative_phone, "444-444-4444")

        self.assertEqual(updated_application.customer.name, 'Brandon1 Kirchner1')
        self.assertEqual(updated_application.customer.phone, '512-111-1111')

        self.assertEqual(updated_application.current_home.address.street, '4007 Lillian Lane')
        self.assertEqual(updated_application.current_home.address.city, 'Austin')
        self.assertEqual(updated_application.current_home.address.state, 'Texas')
        self.assertEqual(updated_application.current_home.address.zip, '78749')
        self.assertEqual(updated_application.current_home.outstanding_loan_amount, 123000.00)

        self.assertEqual(updated_application.mortgage_lender.email, 'bob@bank.com')
        self.assertEqual(updated_application.mortgage_lender.name, 'Bob Banker')
        self.assertEqual(updated_application.mortgage_lender.phone, '512-333-3333')

        self.assertEqual(updated_application.listing_agent.name, 'Sydne Kleespies')
        self.assertEqual(updated_application.listing_agent.phone, '2222222222')
        self.assertEqual(updated_application.listing_agent.email, 'sydne@homeward.com')
        self.assertEqual(updated_application.listing_agent.company, 'Kleespies Group')

        self.assertEqual(updated_application.buying_agent.name, 'Sydne Kleespies')
        self.assertEqual(updated_application.buying_agent.phone, '2222222222')
        self.assertEqual(updated_application.buying_agent.email, 'sydne@homeward.com')
        self.assertEqual(updated_application.buying_agent.company, 'Kleespies Group')

        self.assertEqual(updated_application.offer_property_address.street, "306 Plum Lane")
        self.assertEqual(updated_application.offer_property_address.city, "Chapel Hill")
        self.assertEqual(updated_application.offer_property_address.state, "NC")
        self.assertEqual(updated_application.offer_property_address.zip, "27514")

        self.assertEqual(updated_application.cx_manager.id, existing_cx_manager.id)
        self.assertEqual(updated_application.cx_manager.email, "test.cx@homeward.com")
        self.assertEqual(updated_application.cx_manager.bio, "Some BIO...")
        self.assertEqual(updated_application.cx_manager.first_name, "Test")
        self.assertEqual(updated_application.cx_manager.last_name, "CX")
        self.assertEqual(updated_application.cx_manager.phone, "1111111111")
        self.assertEqual(updated_application.cx_manager.schedule_a_call_url, "testurl.homeward.com")
        self.assertEqual(updated_application.cx_manager.photo_url, "testurl.homeward.com")

        self.assertEqual(StageHistory.objects.count(), 1)

    @patch("utils.salesforce.homeward_salesforce.get_user_by_id")
    @patch("utils.salesforce.homeward_salesforce.get_account_by_id")
    def test_should_bulk_update_record_from_salesforce(self, sf_account_mock, sf_user_mock):
        sf_account_mock.return_value = {
            Customer.FIRST_NAME_FIELD: 'Sydne',
            Customer.LAST_NAME_FIELD: 'Kleespies',
            Customer.PHONE_FIELD: '2222222222',
            Customer.EMAIL_FIELD: 'sydne@homeward.com',
            RealEstateAgent.BUYING_AGENT_COMPANY_FIELD: 'Kleespies Group'
        }
        sf_user_mock.return_value = {
            InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
            InternalSupportUser.USER_BIO: "Some BIO...",
            InternalSupportUser.USER_FIRST_NAME: "Test",
            InternalSupportUser.USER_LAST_NAME: "CX",
            InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
            InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
            InternalSupportUser.USER_PROFILE_NAME: "CXA",
            InternalSupportUser.ID_FIELD: "0054P00000AStdhQAD"
        }

        customer = Customer.objects.create(name='Brandon Kirchner', email='brandon@homeward.com', phone='512-923-5534')
        current_home = self.create_currenthome('sf')
        agent = RealEstateAgent.objects.create(name='Ronald Realtor', phone='777-777-7777', email='ronald@realtor.com',
                                               company='Real Estate Business')
        lender = MortgageLender.objects.create(name='Larry Lender', email='larry@lender.com', phone='999-999-9999')
        offer_property_address = Address.objects.create(**get_fake_address('test'))
        Application.objects.create(customer=customer, lead_source='blah', lead_source_drill_down_1='boop',
                                   stage=ApplicationStage.INCOMPLETE, current_home=current_home,
                                   min_price=150000, max_price=350000, move_in='0-3 months',
                                   shopping_location='Portland, Oregon USA', real_estate_agent=agent,
                                   mortgage_lender=lender, self_reported_referral_source='news_article',
                                   self_reported_referral_source_detail='colin told me',
                                   home_buying_stage=HomeBuyingStage.MAKING_OFFERS, internal_referral='blah',
                                   offer_property_address=offer_property_address,
                                   product_offering=ProductOffering.BUY_ONLY)

        module_dir = os.path.dirname(__file__)
        data = open(os.path.join(module_dir, '../static/bulk_sf_record.json')).read()
        url = '/api/1.0.0/application/salesforce/bulk/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, json.loads(data), **headers, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_application = Application.objects.filter(customer__email=customer.email).first()

        self.assertEqual(updated_application.move_in, '3-6 months')
        self.assertEqual(updated_application.min_price, 250000)
        self.assertEqual(updated_application.max_price, 450000)
        self.assertEqual(updated_application.self_reported_referral_source, 'news_article')
        self.assertEqual(updated_application.self_reported_referral_source_detail, 'telephone')
        self.assertEqual(updated_application.home_buying_stage, 'Making an offer')
        self.assertEqual(updated_application.lead_source, 'Direct')
        self.assertEqual(updated_application.lead_source_drill_down_1, 'Apple')
        self.assertEqual(updated_application.lead_status, 'Qualified')
        self.assertEqual(updated_application.stage, 'complete')
        self.assertEqual(updated_application.internal_referral, 'blahblah')
        self.assertEqual(updated_application.product_offering, ProductOffering.BUY_SELL.value)

        self.assertEqual(updated_application.builder.representative_name, 'Brian Builder')
        self.assertEqual(updated_application.builder.company_name, 'MHI')
        self.assertEqual(updated_application.builder.representative_email, "brian@builder.com")
        self.assertEqual(updated_application.builder.representative_phone, "444-444-4444")

        self.assertEqual(updated_application.customer.name, 'Brandon1 Kirchner1')
        self.assertEqual(updated_application.customer.phone, '512-111-1111')

        self.assertEqual(updated_application.current_home.address.street, '4007 Lillian Lane')
        self.assertEqual(updated_application.current_home.address.city, 'Austin')
        self.assertEqual(updated_application.current_home.address.state, 'Texas')
        self.assertEqual(updated_application.current_home.address.zip, '78749')
        self.assertEqual(updated_application.current_home.outstanding_loan_amount, 123000.00)
        self.assertEqual(updated_application.current_home.market_value, 3565656)

        self.assertEqual(updated_application.mortgage_lender.email, 'bob@bank.com')
        self.assertEqual(updated_application.mortgage_lender.name, 'Bob Banker')
        self.assertEqual(updated_application.mortgage_lender.phone, '512-333-3333')

        self.assertEqual(updated_application.listing_agent.name, 'Sydne Kleespies')
        self.assertEqual(updated_application.listing_agent.phone, '2222222222')
        self.assertEqual(updated_application.listing_agent.email, 'sydne@homeward.com')
        self.assertEqual(updated_application.listing_agent.company, 'Kleespies Group')

        self.assertEqual(updated_application.buying_agent.name, 'Sydne Kleespies')
        self.assertEqual(updated_application.buying_agent.phone, '2222222222')
        self.assertEqual(updated_application.buying_agent.email, 'sydne@homeward.com')
        self.assertEqual(updated_application.buying_agent.company, 'Kleespies Group')

        self.assertEqual(updated_application.offer_property_address.street, "306 Plum Lane")
        self.assertEqual(updated_application.offer_property_address.city, "Chapel Hill")
        self.assertEqual(updated_application.offer_property_address.state, "NC")
        self.assertEqual(updated_application.offer_property_address.zip, "27514")

        self.assertEqual(updated_application.mortgage_status, 'VPAL started')
        self.assertEqual(updated_application.homeward_owner_email, 'brandon@test.com')

        self.assertAlmostEqual(updated_application.preapproval.amount, Decimal(123456.78))
        self.assertAlmostEqual(updated_application.preapproval.estimated_down_payment, Decimal(9876.54))
        self.assertEqual(updated_application.preapproval.vpal_approval_date, datetime.date(2020, 6, 30))

        self.assertEqual(updated_application.new_home_purchase.option_period_end_date, datetime.date(2020, 6, 17))
        self.assertEqual(updated_application.new_home_purchase.homeward_purchase_close_date, datetime.date(2020, 6, 30))
        self.assertEqual(updated_application.new_home_purchase.customer_purchase_close_date, datetime.date(2020, 7, 30))
        self.assertAlmostEqual(updated_application.new_home_purchase.contract_price, Decimal(523234.45))
        self.assertAlmostEqual(updated_application.new_home_purchase.earnest_deposit_percentage, Decimal(2))
        self.assertEqual(updated_application.new_home_purchase.address.street, '306 Plum Lane')
        self.assertEqual(updated_application.new_home_purchase.address.city, 'Chapel Hill')
        self.assertEqual(updated_application.new_home_purchase.address.state, 'NC')
        self.assertEqual(updated_application.new_home_purchase.address.zip, '27514')

        self.assertEqual(StageHistory.objects.count(), 1)

    @patch("utils.salesforce.homeward_salesforce.get_account_by_id")
    @patch("utils.salesforce.homeward_salesforce.get_user_by_id")
    def test_should_create_entities_that_dont_exist_if_created_in_sf(self, sf_user_mock, sf_account_mock):
        sf_account_mock.return_value = {
            Customer.FIRST_NAME_FIELD: 'Sydne',
            Customer.LAST_NAME_FIELD: 'Kleespies',
            Customer.PHONE_FIELD: '2222222222',
            Customer.EMAIL_FIELD: 'sydne@homeward.com',
            RealEstateAgent.BUYING_AGENT_COMPANY_FIELD: 'Kleespies Group'
        }

        sf_user_mock.return_value = {
            InternalSupportUser.USER_EMAIL: "test.cx@homeward.com",
            InternalSupportUser.USER_BIO: "Some BIO...",
            InternalSupportUser.USER_FIRST_NAME: "Test",
            InternalSupportUser.USER_LAST_NAME: "CX",
            InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "testurl.homeward.com",
            InternalSupportUser.USER_PHOTO_URL: "testurl.homeward.com",
            InternalSupportUser.USER_PROFILE_NAME: "CXA",
            InternalSupportUser.ID_FIELD: "0054P00000B7PQcQAN"
        }

        customer = Customer.objects.create(name='Brandon Kirchner', email='brandon@homeward.com', phone='512-923-5534')
        existing_cx_manager = random_internal_support_user()
        Application.objects.create(lead_source='blah', lead_source_drill_down_1='boop', customer=customer,
                                   stage=ApplicationStage.INCOMPLETE,
                                   min_price=150000, max_price=350000, move_in='0-3 months',
                                   shopping_location='Portland, Oregon USA',
                                   self_reported_referral_source='news_article',
                                   self_reported_referral_source_detail='telephone',
                                   home_buying_stage=HomeBuyingStage.MAKING_OFFERS, cx_manager=existing_cx_manager)

        module_dir = os.path.dirname(__file__)
        data = open(os.path.join(module_dir, '../static/sf_record.json')).read()
        url = '/api/1.0.0/application/salesforce/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        self.client.post(url, json.loads(data), **headers, format='json')

        updated_application = Application.objects.filter(customer__email=customer.email).first()

        self.assertEqual(updated_application.move_in, '3-6 months')
        self.assertEqual(updated_application.min_price, 250000)
        self.assertEqual(updated_application.max_price, 450000)
        self.assertEqual(updated_application.self_reported_referral_source, 'news_article')
        self.assertEqual(updated_application.self_reported_referral_source_detail, 'telephone')
        self.assertEqual(updated_application.home_buying_stage, 'Making an offer')
        self.assertEqual(updated_application.lead_source, 'Direct')
        self.assertEqual(updated_application.lead_source_drill_down_1, 'Apple')
        self.assertEqual(updated_application.lead_status, 'Qualified')
        self.assertEqual(updated_application.stage, 'complete')
        self.assertEqual(updated_application.reason_for_trash, "Couldn't give them a Floor Price on their home")

        self.assertEqual(updated_application.builder.representative_name, 'Brian Builder')
        self.assertEqual(updated_application.builder.company_name, 'MHI')
        self.assertEqual(updated_application.builder.representative_email, "brian@builder.com")
        self.assertEqual(updated_application.builder.representative_phone, "444-444-4444")

        self.assertEqual(updated_application.customer.name, 'Brandon1 Kirchner1')
        self.assertEqual(updated_application.customer.phone, '512-111-1111')

        self.assertEqual(updated_application.current_home.address.street, '4007 Lillian Lane')
        self.assertEqual(updated_application.current_home.address.city, 'Austin')
        self.assertEqual(updated_application.current_home.address.state, 'Texas')
        self.assertEqual(updated_application.current_home.address.zip, '78749')
        self.assertEqual(updated_application.current_home.outstanding_loan_amount, 123000.00)

        self.assertEqual(updated_application.mortgage_lender.email, 'bob@bank.com')
        self.assertEqual(updated_application.mortgage_lender.name, 'Bob Banker')
        self.assertEqual(updated_application.mortgage_lender.phone, '512-333-3333')

        self.assertEqual(updated_application.listing_agent.name, 'Sydne Kleespies')
        self.assertEqual(updated_application.listing_agent.phone, '2222222222')
        self.assertEqual(updated_application.listing_agent.email, 'sydne@homeward.com')
        self.assertEqual(updated_application.listing_agent.company, 'Kleespies Group')

        self.assertEqual(updated_application.buying_agent.name, 'Sydne Kleespies')
        self.assertEqual(updated_application.buying_agent.phone, '2222222222')
        self.assertEqual(updated_application.buying_agent.email, 'sydne@homeward.com')
        self.assertEqual(updated_application.buying_agent.company, 'Kleespies Group')

        self.assertEqual(updated_application.offer_property_address.street, "306 Plum Lane")
        self.assertEqual(updated_application.offer_property_address.city, "Chapel Hill")
        self.assertEqual(updated_application.offer_property_address.state, "NC")
        self.assertEqual(updated_application.offer_property_address.zip, "27514")

        #Should not update old cx!
        self.assertNotEqual(updated_application.cx_manager.id, existing_cx_manager.id)

        self.assertEqual(updated_application.cx_manager.email, "test.cx@homeward.com")
        self.assertEqual(updated_application.cx_manager.bio, "Some BIO...")
        self.assertEqual(updated_application.cx_manager.first_name, "Test")
        self.assertEqual(updated_application.cx_manager.last_name, "CX")
        self.assertEqual(updated_application.cx_manager.schedule_a_call_url, "testurl.homeward.com")
        self.assertEqual(updated_application.cx_manager.photo_url, "testurl.homeward.com")

    @patch("utils.salesforce.homeward_salesforce.get_account_by_id")
    @patch("utils.salesforce.homeward_salesforce.get_user_by_id")
    def test_should_not_update_cx_if_owner_is_not_cx(self, sf_user_mock, sf_account_mock):
        sf_user_mock.return_value = {
            InternalSupportUser.USER_EMAIL: "new.notcx@homeward.com",
            InternalSupportUser.USER_BIO: "New BIO...",
            InternalSupportUser.USER_FIRST_NAME: "New",
            InternalSupportUser.USER_LAST_NAME: "New",
            InternalSupportUser.USER_PHONE: "1211211211",
            InternalSupportUser.USER_SCHEDULE_A_CALL_URL: "new.homeward.com",
            InternalSupportUser.USER_PHOTO_URL: "new.homeward.com",
            InternalSupportUser.ID_FIELD: "0054P00000B7PQcQAN"
        }
        sf_account_mock.return_value = {
            Customer.FIRST_NAME_FIELD: 'Sydne',
            Customer.LAST_NAME_FIELD: 'Kleespies',
            Customer.PHONE_FIELD: '2222222222',
            Customer.EMAIL_FIELD: 'sydne@homeward.com',
            RealEstateAgent.BUYING_AGENT_COMPANY_FIELD: 'Kleespies Group',
            InternalSupportUser.USER_PROFILE_NAME: "Some Other Profile Type"
        }
        existing_cx = InternalSupportUser.objects.create(
            sf_id='0054P00000AStdhQAD',
            email="test.cx@homeward.com",
            first_name="test",
            last_name="manager",
            photo_url="testurl.homeward.com",
            bio="test bio",
            schedule_a_call_url="testurl.homeward.com"
    )
        customer = Customer.objects.create(name='Brandon Kirchner', email='brandon@homeward.com', phone='512-923-5534')
        current_home = self.create_currenthome('sf')
        agent = RealEstateAgent.objects.create(name='Ronald Realtor', phone='777-777-7777', email='ronald@realtor.com',
                                               company='Real Estate Business')
        lender = MortgageLender.objects.create(name='Larry Lender', email='larry@lender.com', phone='999-999-9999')
        offer_property_address = Address.objects.create(**get_fake_address('test'))
        Application.objects.create(customer=customer, lead_source='blah', lead_source_drill_down_1='boop',
                                   stage=ApplicationStage.INCOMPLETE, current_home=current_home,
                                   min_price=150000, max_price=350000, move_in='0-3 months',
                                   shopping_location='Portland, Oregon USA', real_estate_agent=agent,
                                   mortgage_lender=lender, self_reported_referral_source='news_article',
                                   self_reported_referral_source_detail='colin told me',
                                   home_buying_stage=HomeBuyingStage.MAKING_OFFERS, internal_referral='blah',
                                   offer_property_address=offer_property_address, cx_manager=existing_cx)
        module_dir = os.path.dirname(__file__)
        data = open(os.path.join(module_dir, '../static/sf_record.json')).read()
        url = '/api/1.0.0/application/salesforce/'
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        self.client.post(url, json.loads(data), **headers, format='json')

        updated_app = Application.objects.get(customer__email=customer.email)
        cx_manager = updated_app.cx_manager
        self.assertEqual(cx_manager, existing_cx)

    def test_should_create_stage_history(self):
        application = self.create_application('stage_history')
        self.assertEqual(StageHistory.objects.all().count(), 0)

        application.stage = ApplicationStage.APPROVED
        application.save()

        self.assertEqual(StageHistory.objects.all().count(), 1)
        stage_history = application.stagehistory_set.first()
        self.assertEqual(stage_history.previous_stage, ApplicationStage.COMPLETE)
        self.assertEqual(stage_history.new_stage, ApplicationStage.APPROVED)

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        self.assertEqual(StageHistory.objects.all().count(), 2)
