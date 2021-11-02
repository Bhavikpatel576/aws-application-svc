from unittest.mock import call, patch, MagicMock, Mock

from rest_framework.test import APITestCase

from application.models.address import Address
from application.models.offer import Offer, OfferStatus
from application.tests import random_objects
from application.tests.random_objects import fake

class OfferModelTests(APITestCase):

    def setUp(self) -> None:
        self.address = Address.objects.create(**{
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            })

        self.application = random_objects.random_application()
        self.offer = random_objects.random_offer(application=self.application)
    
    def test_should_default_status_to_incomplete(self):
        self.assertEqual(self.offer.status, "Incomplete")
    
    @patch("application.models.pricing.homeward_salesforce")
    def test_converting_to_salesforce_payload(self, hw_sf_patch):
        hw_sf_patch.create_new_salesforce_object.return_value = random_objects.fake.pystr(max_chars=18)

        application = random_objects.random_application(new_salesforce=fake.pystr(max_chars=18))
        offer = random_objects.random_offer(application=application)
        actual_payload = offer.salesforce_field_mapping()
        self.assertEqual(actual_payload['Year_Home_Built__c'], offer.year_built)
        self.assertEqual(actual_payload['Home_Square_Footage__c'], offer.home_square_footage)
        self.assertEqual(actual_payload['New_Home_Property_Type__c'], offer.property_type)
        self.assertEqual(actual_payload['New_Home_Less_Than_1_Acre__c'], 'Yes' if offer.less_than_one_acre else 'No')
        self.assertEqual(actual_payload['New_Home_List_Price__c'], offer.home_list_price)
        self.assertEqual(actual_payload['New_Home_Offer_Price__c'], offer.offer_price)
        self.assertEqual(actual_payload['Contract_Type__c'], offer.contract_type)
        self.assertEqual(actual_payload['Funding_Type__c'], offer.funding_type)
        self.assertEqual(actual_payload['Finance_Approved_Closed_Date__c'], offer.finance_approved_close_date)
        self.assertEqual(actual_payload[Offer.ADDRESS_STREET_FIELD], offer.offer_property_address.street)
        self.assertEqual(actual_payload[Offer.ADDRESS_CITY_FIELD], offer.offer_property_address.city)
        self.assertEqual(actual_payload[Offer.ADDRESS_STATE_FIELD], offer.offer_property_address.state)
        self.assertEqual(actual_payload[Offer.ADDRESS_ZIP_FIELD], offer.offer_property_address.zip)
    
    @patch("application.models.pricing.homeward_salesforce.create_new_salesforce_object")
    def test_push_to_salesforce_when_complete(self, push_to_sf_patch):
        push_to_sf_patch.create_new_salesforce_object.return_value = random_objects.fake.pystr(max_chars=18)

        application = random_objects.random_application(new_salesforce=fake.pystr(max_chars=18))
        offer = random_objects.random_offer(application=application)
        offer.status = OfferStatus.COMPLETE
        push_to_sf_patch.create_new_salesforce_object(offer.to_salesforce_representation(), offer.salesforce_object_type)
        create_call = [call.create_new_salesforce_object(offer.to_salesforce_representation(), offer.salesforce_object_type)]
        push_to_sf_patch.assert_has_calls(create_call)

    @patch("application.models.pricing.homeward_salesforce.create_new_salesforce_object")
    def test_should_not_push_offer_to_salesforce_if_incomplete(self, push_to_sf_patch):
        application = random_objects.random_application()
        offer = random_objects.random_offer(application=application)
        offer.save()
        push_to_sf_patch.assert_not_called()
    
    @patch("application.models.pricing.homeward_salesforce.update_salesforce_object")
    def test_should_update_salesforce_offer_when_sf_id_present(self, update_sf_object_patch):
        application = random_objects.random_application(new_salesforce=fake.pystr(max_chars=18))
        offer = random_objects.random_offer(application=application)
        offer.status = OfferStatus.COMPLETE
        offer.salesforce_id = random_objects.fake.pystr(max_chars=18)
        offer.save()

        offer.year_built = 2020
        offer.save()
        update_sf_object_patch.update_salesforce_object(offer.salesforce_id, offer.to_salesforce_representation(), offer.salesforce_object_type)
        create_call = [call.update_salesforce_object(offer.salesforce_id, offer.to_salesforce_representation(), offer.salesforce_object_type)]
        update_sf_object_patch.assert_has_calls(create_call)

    @patch('application.models.offer.PropertyDataAggregatorClient')
    def test_office_name_set_by_enrich(self, pda_mock):
        fake_office_name_from_pda = "Fake Realty Office"
        fake_office_name_locally = 'fake office name'
        pda_mock.return_value.get_listing.return_value = {'year_built': 1999, 'office_name': fake_office_name_from_pda}
        application = random_objects.random_application()
        offer_property_address = Address.objects.create(street='3211 Test Rd.', city='Austin', state='TX', zip='78704')
        offer = Offer.objects.create(property_type='Single Family',
                                     contract_type='Resale',
                                     other_offers='No',
                                     pda_listing_uuid='2ce3ab03-5042-43ad-9cc5-b82c6d94b08b',
                                     plan_to_lease_back_to_seller='No',
                                     less_than_one_acre=True,
                                     waive_appraisal=True,
                                     already_under_contract=True,
                                     hoa=True,
                                     preferred_closing_date='2021-05-26',
                                     offer_price=500000,
                                     offer_property_address=offer_property_address,
                                     application=application,
                                     year_built=1999,
                                     funding_type=None,
                                     office_name=fake_office_name_locally)
        offer.save()
        assert offer.office_name == fake_office_name_from_pda
