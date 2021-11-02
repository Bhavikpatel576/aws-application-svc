from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import Application
from application.models.customer import Customer
from application.task_operations import run_task_operations


class TaskStatusTests(AuthMixin, APITestCase):
    def test_task_status_has_is_actionable_and_is_editable(self):
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)

        run_task_operations(application)

        url = '/api/1.0.0/application/task-status/'

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.get(url, **headers, format='json')
        self.assertEqual(response.status_code, 200)

        for task in response.json():
            self.assertEqual(task.get('is_actionable'), True)
            self.assertEqual(task.get('task_obj').get('is_editable'), False)
