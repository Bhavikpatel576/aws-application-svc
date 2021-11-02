from rest_framework.test import APITestCase

from application.models.floor_price import FloorPrice, FloorPriceType
from application.tests import random_objects


class ApplicationModelTests(APITestCase):
    def test_formatting_floor_price(self):
        app = random_objects.random_application()
        self.assertEqual(app.get_formatted_floor_price(), "Your Homeward transaction does not include a floor price")

        app.current_home = random_objects.random_current_home()
        app.save()
        self.assertEqual(app.get_formatted_floor_price(), "Your Homeward transaction does not include a floor price")

        app.current_home.floor_price = FloorPrice.objects.create(preliminary_amount=123456.78,
                                                                 type=FloorPriceType.REQUIRED)
        app.save()
        self.assertEqual(app.get_formatted_floor_price(), "$123,457 (estimated)")

        app.current_home.floor_price.amount = 876543.21
        app.save()
        self.assertEqual(app.get_formatted_floor_price(), "$876,543")

        app.current_home.floor_price.type = FloorPriceType.NONE
        app.current_home.floor_price.save()
        self.assertEqual(app.get_formatted_floor_price(), "Your Homeward transaction does not include a floor price")
