from django.core.management.base import BaseCommand
from django.utils import timezone

from knox.models import AuthToken

from rest_framework.test import APIClient

from api.v1_0_0.tests._utils import data_generators

from application.models.application import Application
from application.models.customer import Customer
from application.models.real_estate_agent import RealEstateAgent
from application.models.offer import Offer

from user.models import User


class Command(BaseCommand):
    """ Run command: pipenv run python src/manage.py offer_api_test_cases """

    def handle(self, *args, **options):
        """ ################################### SETUP ################################### """
        # Create or find your own user with your test agent email address
        # Make sure the user is in Staging SSO with the same email address (Should be in verified email and claimed
        # agent groups)
        # Locally set your user's username to the id of the user in Staging SSO (Ex: user.username = '1234')
        user = User.objects.get(email='your-test-agent-email-here')
        token = AuthToken.objects.create(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': f'Token {token}'
        }

        """ ################################### GET ################################### """
        # client = APIClient()
        # offer = Offer.objects.get(id='513c3f53-9ee3-4e8e-90ae-07970a02b34c')
        # # offer = Offer.objects.filter(application__buying_agent__email=user.email).first()
        # url = f'/api/1.0.0/offer/{offer.id}/'
        #
        # response = client.get(url, **headers, format='json')
        # print(response.content)

        """ ################################### POST ################################### """
        # # application = Application.objects.filter(buying_agent__email=user.email).first()
        # customer = Customer.objects.get(email="rachel.peace+testcustomer@homeward.com")
        # agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent",
        #                                                                                     email=user.email))
        #
        # app_data = data_generators.get_fake_application("austin", buying_agent=agent)
        # app_data["customer"] = customer
        #
        # application = Application.objects.create(**app_data)
        # # application.stage = 'approved'
        # application.stage = 'qualified application'
        # application.save()
        #
        # request_data = {
        #                 'year_built': 2012,
        #                 'home_square_footage': 1300,
        #                 'property_type': 'Single Family',
        #                 'less_than_one_acre': True,
        #                 'home_list_price': 500000,
        #                 "offer_price": 510000,
        #                 "contract_type": "Resale",
        #                 "other_offers": "1-4",
        #                 "offer_deadline": timezone.now(),
        #                 "plan_to_lease_back_to_seller": "No",
        #                 "waive_appraisal": "Yes",
        #                 "already_under_contract": True,
        #                 "comments": "test comments",
        #                 "application_id": application.id,
        #                 "offer_property_address": {
        #                     "street": "2222 Test St.",
        #                     "city": "Austin",
        #                     "state": "TX",
        #                     "zip": 78704
        #                 }
        #             }
        #
        # url = ('/api/1.0.0/offer/')
        # client = APIClient()
        # response = client.post(url, request_data, **headers, format='json')
        # print(response.content)

        """ ################################### PATCH ################################### """
        # offer = Offer.objects.get(id='805912bf-913b-4f8d-ae5e-39512f7d10b9')
        # # offer = Offer.objects.filter(application__buying_agent__email=user.email).first()
        # client = APIClient()
        # url = '/api/1.0.0/offer/{}/'.format(offer.id)
        #
        # data = {
        #     "application_id": offer.application.id,
        #     "year_built": 2007
        # }
        #
        # response = client.patch(url, data, **headers, format='json')
        # print(response.content)
