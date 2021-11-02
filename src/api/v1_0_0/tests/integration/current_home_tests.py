"""
Test cases for current home.
"""
import os
from pathlib import Path
from application.models.application import ProductOffering
from application.task_operations import run_task_operations
from application.models.task import Task
from application.models.task_progress import TaskProgress
from application.models.task_name import TaskName
from application.models.models import CurrentHomeImage

from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import Application
from application.models.current_home import CurrentHome
from application.tests.random_objects import fake
from application.models.task import Task
from application.models.task_name import TaskName
from application.models.task_progress import TaskProgress
from application.task_operations import run_task_operations
from user.models import User


class CurrentHomeTests(AuthMixin, APITestCase):
    module_dir = str(Path(__file__).parent)
    fixtures = [os.path.join(module_dir, "../static/current_home_test_fixture.json")]

    def setUp(self):
        self.current_home = CurrentHome.objects.get(pk="74d75877-fefc-40cd-8479-7c2008eb7774")
        self.application = Application.objects.get(pk="aca30e9e-776b-44fb-ba37-93e4b195cefe")
        self.user = User.objects.get(pk=1)

    @patch("application.signals.get_partner")
    @patch("application.tasks.push_current_home_to_salesforce.apply_async")
    def test_update_current_home(self, push_to_sf_patch, get_partner_patch):
        get_partner_patch.return_value = {}
        self.current_home.listing_status = None
        self.current_home.customer_value_opinion = None
        self.current_home.save()
        
        run_task_operations(self.application)
        current_home_task = Task.objects.get(name=TaskName.EXISTING_PROPERTY)
        current_home_task_status = self.application.task_statuses.get(task_obj=current_home_task)
        self.assertEqual(TaskProgress.NOT_STARTED, current_home_task_status.status)
        
        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        payload = {
            "listing_url": "http://www.newlistingurl.homeward.com",
            "customer_value_opinion": "400000.00",
            "salesforce_id": "new-salesforce-id"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 200)
        self.current_home.refresh_from_db()
        current_home_task_status.refresh_from_db()
        self.assertEqual(self.current_home.listing_url, "http://www.newlistingurl.homeward.com")
        self.assertEqual(self.current_home.customer_value_opinion, 400000.00)
        self.assertEqual(TaskProgress.COMPLETED, current_home_task_status.status)
        # should not update
        self.assertEqual(self.application.current_home.salesforce_id, 'some-salesforce-id')
        push_to_sf_patch.assert_called_once()

    @patch("application.signals.get_partner")
    def test_cant_update_current_home_of_other_user(self, get_partner_patch):
        get_partner_patch.return_value = {}
        self.application.customer.email="some-other-email@gmai.com"
        self.application.customer.save()

        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        payload = {
            "listing_url": "http://www.newlistingurl.homeward.com",
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 403)
        self.current_home.refresh_from_db()
        # Current home is unchanged
        self.assertEqual(self.current_home.listing_url, "https://listing-site.com/my-listing-id")

    @patch("application.signals.get_partner")
    def test_update_current_home_bad_request(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        payload = {
            "listing_url": "not a url"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 400)

    @patch("application.signals.get_partner")
    def test_update_current_home_does_not_exist(self, get_partner_patch):
        get_partner_patch.return_value = {}
        self.application.current_home = None
        self.application.save()
        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        payload = {
            "listing_url": "not a url"
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.patch(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 404)
    
    @patch("application.signals.get_partner")
    def test_create_current_home_already_exists(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        payload = {
            "listing_url": "http://www.newlistingurl.homeward.com",
            "address": { 
                "street": "1 Main Street",
                "city": "Brooklyn",
                "state": "NY",
                "zip": "11201",
                "unit": "B"
            },
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 409)
        self.current_home.refresh_from_db()
        # Current home is unchanged
        self.assertEqual(self.current_home.listing_url, "https://listing-site.com/my-listing-id")

    @patch("application.signals.get_partner")
    def test_create_current_home_requires_address(self, get_partner_patch):
        get_partner_patch.return_value = {}
        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        self.application.current_home = None
        self.application.save()
        payload = {
            "listing_url": "http://www.newlistingurl.homeward.com",
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, payload, **headers, format='json')
        self.assertEqual(response.status_code, 400)
        self.current_home.refresh_from_db()
        # Current home is unchanged
        self.assertEqual(self.current_home.listing_url, "https://listing-site.com/my-listing-id")

    @patch("application.signals.get_partner")
    @patch("application.tasks.push_current_home_to_salesforce.apply_async")
    def test_create_current_home(self, push_to_sf_patch, get_partner_patch):
        get_partner_patch.return_value = {}
        url = f'/api/1.0.0/application/{self.application.id}/current-home/'
        token = self.login_user(self.user)[1]
        self.application.current_home = None
        self.application.save()
        payload = {
            "address": { 
                "street": "1 Main Street",
                "city": "Brooklyn",
                "state": "NY",
                "zip": "11201",
                "unit": "B"
                },
            "closing_date": "2020-09-30T00:00:00Z",
            "final_sales_price": "123456.00",
            "market_value": "10000000.00",
            "outstanding_loan_amount": "200000.00",
            "customer_value_opinion": "10000000.00",
            "attributes": "10000000.00",
            "listing_status": "Under Contract",
            "listing_url": "https://listing-site.com/my-listing-id",
            "total_concession_amount": "50000.00",
            "option_period_expiration_date": "2020-09-30T00:00:00Z",
            "floors_count": 2,
            "bedrooms_count": 4,
            "master_on_main": True,
            "home_size_sq_ft": 40000,
            "has_made_addition": True,
            "addition_type": "unpermitted addition",
            "addition_size_sq_ft": 3000,
            "has_basement": True,
            "basement_type": "finished",
            "basement_size_sq_ft": 1000,
            "kitchen_countertop_type": "corian",
            "kitchen_appliance_type": "stainless steel",
            "kitchen_features": ["tile backsplash", "new cabinets"],
            "kitchen_has_been_remodeled": "less than 5 years ago",
            "master_bathroom_condition": "some scuffs, stains, or scratches",
            "full_bathrooms_count": 4,
            "partial_bathrooms_count": 2,
            "interior_walls_condition": "Needs some work",
            "flooring_types": ["Hardwood", "Tile", "Carpet"],
            "hardwood_flooring_condition": "Needs Small Repairs",
            "carpet_flooring_condition": "Needs Cleaning",
            "front_yard_condition": "Minimal Landscaping",
            "back_yard_condition": "Basic Landscaping",
            "exterior_walls_types": ["brick", "stone"],
            "sides_with_masonry_count": "4 side",
            "roof_age_range": "5-10 years old",
            "pool_type": "In-ground",
            "garage_spaces_count": "3",
            "hvac_age_range": "5-10 years old",
            "home_features": ["power lines in front", "gated community"],
            "in_floodzone": "yes",
            "property_view_type": "none",
            "repair_or_update_detail": "I fumigated for fairies.",
            "customer_notes": "Here are a bunch of notes about all the things you really need to know about this property!",
            "under_contract_sales_price": "10000000.00",
            "made_repairs_or_updates": True,
            "anything_needs_repairs": True,
            "outstanding_loan_amount": "20000.00",
            "final_sales_price": "20000.00",
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, payload, **headers, format='json')
        current_home_task = Task.objects.get(name=TaskName.EXISTING_PROPERTY)
        current_home_task_status = self.application.task_statuses.get(task_obj=current_home_task)
        self.assertEqual(TaskProgress.COMPLETED, current_home_task_status.status)
        self.assertEqual(response.status_code, 201)
        self.application.refresh_from_db()
        self.assertEqual(self.application.current_home.listing_url, "https://listing-site.com/my-listing-id")
        self.assertEqual(self.application.current_home.made_repairs_or_updates, True)
        self.assertEqual(self.application.current_home.anything_needs_repairs, True)
        self.assertEqual(self.application.current_home.customer_value_opinion, 10000000.00)
        # should not set
        self.assertEqual(self.application.current_home.outstanding_loan_amount, None)
        self.assertEqual(self.application.current_home.final_sales_price, None)
        push_to_sf_patch.assert_called_once()


class CurrentHomeImageTestCase(AuthMixin, APITestCase):
    """
    CurrentHomeImage Model related test case.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_home_image_url = '/api/1.0.0/current-home-image/'

    def test_without_login(self):
        """
        Test Create API without login.
        """
        application = self.create_application('fakeapplication')
        # Test Post API.
        data = {
            'label': 'kitchen',
            'name': 'abcd.jpg',
            'size': 10000,
            'current_home': application.current_home
        }

        response = self.client.post(self.current_home_image_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test Patch (Update) API.
        current_home_image = self.create_current_home_image('fakehomeimage', application.current_home)
        data = {
            'status': 'uploaded'
        }
        response = self.client.patch("{}{}/".format(self.current_home_image_url, current_home_image.pk), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_api(self):
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')

        # Test with invalid data.
        # 'name' and 'current_home' are required fields.
        data = {
            "size": 20000,
        }
        response = self.client.post(self.current_home_image_url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test with valid data.

        data = {
            "name": "abcd.jpg",
            "label": "kitchen",
            "current_home": application.current_home.pk,
            "size": 306704
        }
        response = self.client.post(self.current_home_image_url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.json()['created_by'])

    def test_create_api_as_user(self):
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')

        data = {
            "name": "abcd.jpg",
            "label": "kitchen",
            "current_home": application.current_home.pk,
            "size": 306704
        }
        response = self.client.post(self.current_home_image_url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_api(self):
        """
        Test create API.
        """
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')
        current_home_image = self.create_current_home_image('fakecurrenthomeimage', application.current_home)

        # Test with invalid data.
        # 'name' and 'current_home' are required fields.
        data = {
            'status': 'invalid_status'  # checking with invalid status option.
        }
        response = self.client.patch('{}{}'.format(self.current_home_image_url, current_home_image.url), data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()
        self.assertEqual(len(errors.keys()), 1)
        self.assertIn('status', errors.keys())

        # In PATCH request, we check if object exists on S3 on CurrentHomeImage.URL
        # If it exists we update the record and if not, we raise validation error.
        # As we don't actually upload images to S3 in test cases.
        # Each URL will get validation error (i.e. 400 status)
        data = {
            'status': 'uploaded'
        }
        response = self.client.patch('{}{}'.format(self.current_home_image_url, current_home_image.url), data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()
        self.assertEqual(len(errors.keys()), 1)
        self.assertIn('url', errors.keys())

    def test_delete_api(self):
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')
        current_home_image = self.create_current_home_image('fakecurrenthomeimage', application.current_home)

        response = self.client.delete('{}{}'.format(self.current_home_image_url, current_home_image.url), **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_api_as_user(self):
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')
        current_home_image = self.create_current_home_image('fakecurrenthomeimage', application.current_home)

        response = self.client.delete('{}{}'.format(self.current_home_image_url, current_home_image.url), **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_api_with_key(self):
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')
        current_home_image = self.create_current_home_image('fakecurrenthomeimage', application.current_home)

        # Test with invalid data.
        # 'name' and 'current_home' are required fields.
        data = {
            'key': 'invalid_key'  # checking with invalid status option.
        }
        response = self.client.patch('{}{}'.format(self.current_home_image_url, current_home_image.url), data,
                                     **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['url'], 'No object found on S3.')

        data = {
            'key': 'test_key'
        }

        response = self.client.patch('{}{}'.format(self.current_home_image_url, current_home_image.url), data,
                                     **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['url'], 'No object found on S3.')

    def test_update_api_as_user(self):
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        application = self.create_application('fakeapplication')
        current_home_image = self.create_current_home_image('fakecurrenthomeimage', application.current_home)

        # Test with invalid data.
        # 'name' and 'current_home' are required fields.
        data = {
            'key': 'invalid_key'  # checking with invalid status option.
        }
        response = self.client.patch('{}{}'.format(self.current_home_image_url, current_home_image.url), data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = {
            "name": "abcd.jpg",
            "label": "kitchen",
            "current_home": application.current_home.pk,
            "size": 306704
        }

        response = self.client.patch('{}{}'.format(self.current_home_image_url, current_home_image.url), data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("utils.hubspot.send_photo_task_complete_notification")
    def test_create_update_task_status(self, email_send_patch):
        photo_task = Task.objects.get(name=TaskName.PHOTO_UPLOAD)
        user = self.create_user('fakeloginuser')
        application = self.create_application('fakeloginuser')
        application.product_offering = ProductOffering.BUY_SELL
        application.save()
        user.email = application.customer.email
        user.save()
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        application_current_home_image_url = f'/api/1.0.0/application/{application.id}/current-home-image/'
        run_task_operations(application)
        CurrentHomeImage.objects.create(url="asdf1.jpg", label="all_other_rooms", current_home=application.current_home)
        CurrentHomeImage.objects.create(url="asdf2.jpg", label="all_other_rooms", current_home=application.current_home)
        CurrentHomeImage.objects.create(url="asdf3.jpg", label="all_other_rooms", current_home=application.current_home)
        CurrentHomeImage.objects.create(url="asdf4.jpg", label="all_other_rooms", current_home=application.current_home)
        # Test with valid data.
        photo_task_status = application.task_statuses.get(task_obj=photo_task)
        self.assertEqual(TaskProgress.NOT_STARTED, photo_task_status.status)
        email_send_patch.assert_not_called()
        data = {
            "name": "abcd4.jpg",
            "label": "all_other_rooms",
            "current_home": application.current_home.pk,
            "size": 306704
        }
        response = self.client.post(application_current_home_image_url, data, **headers)
        photo_task_status.refresh_from_db()
        photo_task_status = application.task_statuses.get(task_obj=photo_task)
        self.assertEqual(TaskProgress.COMPLETED, photo_task_status.status)
        email_send_patch.assert_called_once()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.json()['created_by'])
        # should not send email when task hasn't been moved to completed
        email_send_patch.reset_mock()
        photo_task_status.save()
        email_send_patch.assert_not_called()



    def test_application_current_home_image_create(self):
        user = self.create_user('fakeloginuser')
        application = self.create_application('fakeloginuser')
        application.customer.email = user.email
        application.customer.save()
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        run_task_operations(application)
        application_current_home_image_url = f'/api/1.0.0/application/{application.id}/current-home-image/'


        # Test with invalid data.
        # 'name' and 'current_home' are required fields.
        data = {
            "size": 20000,
        }
        response = self.client.post(application_current_home_image_url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test with valid data.

        data = {
            "name": "abcd.jpg",
            "label": "kitchen",
            "current_home": application.current_home.pk,
            "size": 306704
        }
        response = self.client.post(application_current_home_image_url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.json()['created_by'])


    def test_cant_submit_images_for_other_user(self):
        user = self.create_user('fakeloginuser')
        application = self.create_application('fakeloginuser')
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        run_task_operations(application)
        application_current_home_image_url = f'/api/1.0.0/application/{application.id}/current-home-image/'

        data = {
            "name": "abcd.jpg",
            "label": "kitchen",
            "current_home": application.current_home.pk,
            "size": 306704
        }
        response = self.client.post(application_current_home_image_url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
