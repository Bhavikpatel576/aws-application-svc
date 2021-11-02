"""
Test cases for current home.
"""
import os
from pathlib import Path
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import Application
from application.models.mortgage_lender import MortgageLender
from application.tests import random_objects
from application.tests.random_objects import fake
from user.models import User


class MortgageLenderTests(AuthMixin, APITestCase):
    module_dir = str(Path(__file__).parent)
    fixtures = [os.path.join(module_dir, "../static/current_home_test_fixture.json")]

    def setUp(self):
        self.mortgage_lender = MortgageLender.objects.get(pk="9c07c3e1-1389-4630-b32b-dd36c376c919")
        self.application = Application.objects.get(pk="aca30e9e-776b-44fb-ba37-93e4b195cefe")
        self.user = User.objects.get(pk=1)

    @patch("application.signals.get_partner")
    def test_update_lender(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = '/api/1.0.0/mortgage-lender/application-mortgage-lender/'
        token = self.login_user(self.user)[1]
        payload = {
            "application_id": "aca30e9e-776b-44fb-ba37-93e4b195cefe",
            "name": "New Name",
            "phone": "321-432-5432",
            "email": "someemail@homeward.com"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.put(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.mortgage_lender.name, "New Name")

    @patch("application.signals.get_partner")
    def test_update_mortgage_lender_bad_request(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = '/api/1.0.0/mortgage-lender/application-mortgage-lender/'
        token = self.login_user(self.user)[1]
        payload = {
            "application_id": "aca30e9e-776b-44fb-ba37-93e4b195cefe",
            "name": "Some Name",
            "email": "email@homeward.com"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.put(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 400)

    @patch("application.signals.get_partner")
    def test_update_mortgage_lender_no_application(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = '/api/1.0.0/mortgage-lender/application-mortgage-lender/'
        token = self.login_user(self.user)[1]
        payload = {
            "application_id": "bca30e9e-776b-44fb-ba37-93e4b195cefe",
            "name": "New Name",
            "phone": "321-432-5432",
            "email": "someemail@homeward.com"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.put(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 404)

    @patch("application.signals.get_partner")
    def test_create_mortgage_lender(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = '/api/1.0.0/mortgage-lender/application-mortgage-lender/'
        token = self.login_user(self.user)[1]
        self.application.mortgage_lender = None
        self.application.save()

        payload = {
            "application_id": "aca30e9e-776b-44fb-ba37-93e4b195cefe",
            "name": "New Name",
            "phone": "321-432-5432",
            "email": "someemail@homeward.com"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.put(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 201)
        self.application.refresh_from_db()
        self.assertEqual(self.application.mortgage_lender.name, "New Name")
