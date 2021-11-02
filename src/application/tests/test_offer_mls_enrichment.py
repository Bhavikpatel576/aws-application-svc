import uuid
from decimal import Decimal
from unittest import mock

from rest_framework.test import APITestCase

from application.models.offer import ContractType
from application.tests import random_objects


class TestOfferMLSEnrichment(APITestCase):

    def setUp(self) -> None:
        self.application = random_objects.random_application()

    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_should_pull_listing_info_if_id_present_on_create(self, mock_client):
        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "id": pda_listing_uuid,
            "year_built": 1984,
            "square_feet": 1945,
            "acres": 2.3,
            "listing_price": 123456.78,
            "display_address": "123 Main St.",
            "city": "Austin",
            "state": "Texas",
            "postal_code": "78731"
        }

        mock_client().get_listing.return_value = fake_listing_data

        offer = random_objects.random_offer(application=self.application, pda_listing_uuid=pda_listing_uuid)
        offer.refresh_from_db()

        self.assertEqual(offer.year_built, 1984)
        self.assertEqual(offer.home_square_footage, 1945)
        self.assertEqual(offer.less_than_one_acre, False)
        self.assertAlmostEqual(offer.home_list_price, Decimal(123456.78))
        self.assertEqual(offer.contract_type, ContractType.RESALE)
        self.assertEqual(offer.offer_property_address.street, "123 Main St.")
        self.assertEqual(offer.offer_property_address.city, "Austin")
        self.assertEqual(offer.offer_property_address.state, "Texas")
        self.assertEqual(offer.offer_property_address.zip, "78731")

    @mock.patch('application.models.offer.PropertyDataAggregatorClient')
    def test_should_pull_listing_info_if_id_present_in_offer_update(self, mock_client):
        offer = random_objects.random_offer(application=self.application)

        self.assertIsNone(offer.pda_listing_uuid)

        pda_listing_uuid = uuid.uuid4()

        fake_listing_data = {
            "id": pda_listing_uuid,
            "year_built": 1984,
            "square_feet": 1945,
            "acres": 2.3,
            "listing_price": 123456.78,
            "display_address": "123 Main St.",
            "city": "Austin",
            "state": "Texas",
            "postal_code": "78731"
        }

        mock_client().get_listing.return_value = fake_listing_data

        offer.pda_listing_uuid = pda_listing_uuid
        offer.save()
        offer.refresh_from_db()

        self.assertEqual(offer.year_built, 1984)
        self.assertEqual(offer.home_square_footage, 1945)
        self.assertEqual(offer.less_than_one_acre, False)
        self.assertAlmostEqual(offer.home_list_price, Decimal(123456.78))
        self.assertEqual(offer.contract_type, ContractType.RESALE)
        self.assertEqual(offer.offer_property_address.street, "123 Main St.")
        self.assertEqual(offer.offer_property_address.city, "Austin")
        self.assertEqual(offer.offer_property_address.state, "Texas")
        self.assertEqual(offer.offer_property_address.zip, "78731")
