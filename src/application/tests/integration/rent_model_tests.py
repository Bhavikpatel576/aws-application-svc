from datetime import datetime, timedelta
from decimal import Decimal

from rest_framework.test import APITestCase

from application.models.application import ApplicationStage
from application.models.rent import Rent
from application.tests import random_objects


class RentModelTests(APITestCase):
    def setUp(self):
        self.application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                             stage=ApplicationStage.HOMEWARD_PURCHASE)

        self.application.new_home_purchase.homeward_purchase_close_date = datetime.today().date() - timedelta(days=6)
        self.application.new_home_purchase.customer_purchase_close_date = datetime.today().date() + timedelta(days=6)
        self.application.new_home_purchase.save()

        rent = Rent.objects.create(type='Deferred', amount_months_one_and_two=Decimal('2851.9'),
                                   daily_rental_rate=Decimal('81.73'))

        self.application.new_home_purchase.rent = rent
        self.application.new_home_purchase.save()

    def test_accrued_rent_property(self):
        self.assertEqual(self.application.new_home_purchase.rent.accrued_rent, Decimal('572.11'))

    def test_future_rent_property(self):
        self.assertEqual(self.application.new_home_purchase.rent.future_rent_to_be_charged, Decimal('490.38'))

    def test_total_estimated_rent_property(self):
        self.assertEqual(self.application.new_home_purchase.rent.estimated_total_rent, Decimal('1062.49'))

        self.application.new_home_purchase.rent.total_waived_rent = Decimal('100.00')
        self.application.new_home_purchase.save()

        self.assertEqual(self.application.new_home_purchase.rent.estimated_total_rent, Decimal('962.49'))

        self.application.new_home_purchase.rent.total_leaseback_credit = Decimal('100.00')
        self.application.new_home_purchase.save()

        self.assertEqual(self.application.new_home_purchase.rent.estimated_total_rent, Decimal('862.49'))

    def test_total_estimated_rent_before_credits_property(self):
        self.assertEqual(self.application.new_home_purchase.rent.estimated_total_rent_before_credits, Decimal('1062.49'))

        self.application.new_home_purchase.rent.total_waived_rent = Decimal('100.00')
        self.application.new_home_purchase.save()

        self.assertEqual(self.application.new_home_purchase.rent.estimated_total_rent_before_credits, Decimal('1062.49'))
