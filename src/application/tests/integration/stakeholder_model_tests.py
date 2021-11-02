from django.db.utils import IntegrityError
from application.models.application import Application
from application.tests import random_objects
from application.models.stakeholder import Stakeholder, StakeholderType
from application.models.stakeholder_type import StakeholderType
from rest_framework.test import APITestCase

class StakeholderModelTests(APITestCase):

    def setUp(self) -> None:
        self.application = random_objects.random_application() 

    def test_stakeholder_constraint(self):
        Stakeholder.objects.create(application=self.application, email="someemail@tc.com", type=StakeholderType.TRANSACTION_COORDINATOR)
        with self.assertRaises(IntegrityError):
            Stakeholder.objects.create(application=self.application, email="someemail@tc.com", type=StakeholderType.TRANSACTION_COORDINATOR)
