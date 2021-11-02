import uuid
from unittest.mock import patch

from rest_framework.test import APITestCase

from application.models.address import Address
from application.models.application import ProductOffering
from application.models.brokerage import Brokerage
from application.models.pricing import Pricing
from application.tests import random_objects
from application.tests.random_objects import fake


class PricingModelTests(APITestCase):

    def setUp(self) -> None:
        self.texas_address = Address.objects.create(**{
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            })
        self.colorado_address = Address.objects.create(**{
                "street": "123 Main Street",
                "city": "Denver",
                "state": "CO",
                "zip": "78701"
        })
        self.georgia_address = Address.objects.create(**{
                "street": "123 Main Street",
                "city": "Atlanta",
                "state": "GA",
                "zip": "78701"
            })
    def test_buying_in_georgia(self):
        data = {
            "selling_location": self.georgia_address,
            "buying_location": self.georgia_address,
            "min_price": 123456,
            "max_price": 654321
        }

        pricing = Pricing.objects.create(**data)

        self.assertEqual(pricing.estimated_min_convenience_fee, 1.4)
        self.assertEqual(pricing.estimated_max_convenience_fee, 2.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 151.97)

    def test_georgia_pricing_tiers(self):
        bottom_tier = Pricing.objects.create(buying_location=self.georgia_address,
                                             selling_location=self.georgia_address,
                                             min_price=0, max_price=269999)
        mixed_tier = Pricing.objects.create(buying_location=self.georgia_address, selling_location=self.georgia_address,
                                            min_price=270000, max_price=1000000)
        top_tier = Pricing.objects.create(buying_location=self.georgia_address, selling_location=self.georgia_address,
                                          min_price=300000, max_price=1000000)

        self.assertEqual(bottom_tier.estimated_min_convenience_fee, 1.9)
        self.assertEqual(bottom_tier.estimated_max_convenience_fee, 2.9)

        self.assertEqual(mixed_tier.estimated_min_convenience_fee, 1.4)
        self.assertEqual(mixed_tier.estimated_max_convenience_fee, 2.9)

        self.assertEqual(top_tier.estimated_min_convenience_fee, 1.4)
        self.assertEqual(top_tier.estimated_max_convenience_fee, 2.4)

    def test_buying_in_texas(self):
        data = {
            "selling_location": self.texas_address,
            "buying_location": self.texas_address,
            "min_price": 123456,
            "max_price": 654321
        }

        pricing = Pricing.objects.create(**data)

        self.assertEqual(pricing.estimated_min_convenience_fee, 1.4)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 151.97)

    def test_buying_in_colorado(self):
        data = {
            "selling_location": self.colorado_address,
            "buying_location": self.colorado_address,
            "min_price": 123456,
            "max_price": 654321
        }

        pricing = Pricing.objects.create(**data)

        self.assertEqual(pricing.estimated_min_convenience_fee, 1.4)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 151.97)

    def test_broker_partnership(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = random_objects.random_agent(brokerage=brokerage)

        data = {
            "selling_location": self.texas_address,
            "buying_location": self.texas_address,
            "min_price": 123456,
            "max_price": 654321,
            "agent_id": agent.id
        }

        pricing = Pricing.objects.create(**data)

        self.assertAlmostEqual(pricing.estimated_min_convenience_fee, 1.0)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 151.97)

    def test_invalid_state(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')

        address = Address.objects.create(**{
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            })
        data = {
            "selling_location": address,
            "buying_location": address,
            "min_price": 123456,
            "max_price": 654321,
            "brokerage_id": brokerage.id
        }

        with self.assertRaises(Exception):
            Pricing.calculate_pricing(**data)

    def test_hacky_broker_partnership(self):
        data = {
            "selling_location": self.texas_address,
            "buying_location": self.texas_address,
            "min_price": 123456,
            "max_price": 654321,
            "agents_company": "ra"
        }

        pricing = Pricing.objects.create(**data)

        self.assertAlmostEqual(pricing.estimated_min_convenience_fee, 1.0)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 151.97)

    def test_saving_pricing_with_no_inputs(self):
        pricing = Pricing.objects.create(estimated_min_convenience_fee=1.0, estimated_max_convenience_fee=1.0,
                                         estimated_min_rent_amount=1.0, estimated_max_rent_amount=1.0, min_price=0,
                                         max_price=0)

        self.assertIsNotNone(pricing)

    def test_buy_only_texas_pricing(self):
        pricing = Pricing.objects.create(product_offering=ProductOffering.BUY_ONLY.value,
                                        buying_location=self.texas_address,
                                        min_price=123456, max_price=234567)

        self.assertEqual(pricing.estimated_min_convenience_fee, 0.0)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 54.48)

    def test_buy_only_colorado_pricing(self):
        pricing = Pricing.objects.create(product_offering=ProductOffering.BUY_ONLY.value,
                                        buying_location=self.colorado_address,
                                        min_price=123456, max_price=234567)

        self.assertEqual(pricing.estimated_min_convenience_fee, 0.0)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 28.67)
        self.assertEqual(pricing.estimated_max_rent_amount, 54.48)

    def test_buy_only_georgia_pricing(self):
        pricing = Pricing.objects.create(product_offering=ProductOffering.BUY_ONLY.value,
                                        buying_location=self.georgia_address,
                                        min_price=261000, max_price=291000)

        self.assertEqual(pricing.estimated_min_convenience_fee, 0.0)
        self.assertEqual(pricing.estimated_max_convenience_fee, 1.9)
        self.assertEqual(pricing.estimated_earnest_deposit_percentage, 2.0)
        self.assertEqual(pricing.estimated_min_rent_amount, 60.62)
        self.assertEqual(pricing.estimated_max_rent_amount, 67.59)

    @patch("application.models.pricing.homeward_salesforce")
    def test_converting_to_salesforce_payload(self, hw_sf_patch):
        hw_sf_patch.create_new_salesforce_object.return_value = random_objects.fake.pystr(max_chars=18)

        agent = random_objects.random_agent(sf_id="blah")
        application = random_objects.random_application(new_salesforce=fake.pystr(max_chars=18))
        pricing = random_objects.random_pricing(agent=agent, actions=['saved'],
                                                application=application)
        actual_payload = pricing.salesforce_field_mapping()

        self.assertEqual(actual_payload["Agent__c"], pricing.agent.sf_id)
        self.assertEqual(actual_payload["Agent_Remarks__c"], pricing.agent_remarks)
        self.assertEqual(actual_payload["Agent_Situation__c"], pricing.agent_situation)
        self.assertEqual(actual_payload["Estimated_EMD__c"], pricing.estimated_earnest_deposit_percentage)
        self.assertEqual(actual_payload["Maximum_Convenience_Fee__c"], pricing.estimated_max_convenience_fee)
        self.assertEqual(actual_payload["Maximum_Price__c"], pricing.max_price)
        self.assertEqual(actual_payload["Maximum_Rent_Amount__c"], pricing.estimated_max_rent_amount)
        self.assertEqual(actual_payload["Minimum_Convenience_Fee__c"], pricing.estimated_min_convenience_fee)
        self.assertEqual(actual_payload["Minimum_Price__c"], pricing.min_price)
        self.assertEqual(actual_payload["Minimum_Rent_Amount__c"], pricing.estimated_min_rent_amount)
        self.assertEqual(actual_payload["Property_City__c"], pricing.buying_location.city)
        self.assertEqual(actual_payload["Property_State__c"], pricing.buying_location.state)
        self.assertEqual(actual_payload["Property_Street__c"], pricing.buying_location.street)
        self.assertEqual(actual_payload["Property_Zip__c"], pricing.buying_location.zip)
        self.assertEqual(actual_payload["Saved__c"], True)
        self.assertEqual(actual_payload["Shared__c"], False)
        self.assertEqual(actual_payload["Customer__c"], pricing.application.new_salesforce)
        self.assertEqual(actual_payload["Agent_Quote_Resume_Link__c"], pricing.get_resume_link())

