import locale
import os
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime

from django.test import TestCase

from application.generate_pdf_task import ProcessPdf
from application.models.address import Address
from application.models.offer import PropertyType, ContractType, Offer
from application.models.contract_template import BuyingState
from application.tests import random_objects
from decimal import Decimal

locale.setlocale(locale.LC_ALL, '')


class GeneratePdfTaskTests(TestCase):
    module_dir = str(Path(__file__).parent)
    fixtures = [os.path.join(module_dir, "../static/contract_templates_test_data.json")]

    def create_pdf_offer(self, contract_type: ContractType, property_type: PropertyType, state: BuyingState, year_built: int = 1978, funding_type: str = None):
        application = random_objects.random_application()
        offer_property_address = Address.objects.create(street='3211 Test Rd.', city='Austin', state=state, zip='78704')
        offer_price = Decimal('500000.00')
        offer = Offer.objects.create(property_type=property_type,
                                contract_type=contract_type,
                                other_offers='No',
                                plan_to_lease_back_to_seller='No',
                                less_than_one_acre=True,
                                waive_appraisal=True,
                                already_under_contract=True,
                                hoa=True,
                                preferred_closing_date='2021-05-26',
                                offer_price=offer_price,
                                offer_property_address=offer_property_address,
                                application=application,
                                year_built=year_built,
                                funding_type=funding_type,
                                office_name='Jimmy Drake Realty',
                                mls_listing_id='6230076')
        return offer

    def test_will_create_process_pdf_class_if_offer_conditions_met(self): 
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX)
        pdf = ProcessPdf(offer.id)
        self.assertIsInstance(pdf, ProcessPdf)
    
    def test_will_raise_exception_if_offer_conditions_not_met(self):
        offer = self.create_pdf_offer(ContractType.NEW_BUILD, PropertyType.CONDO, BuyingState.TX)
        with self.assertRaises(Exception):
            ProcessPdf(offer.id)

    def test_will_format_the_pdf_file_name(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX)
        customer_last_name = offer.application.customer.name.split(" ")[-1]

        pdf = ProcessPdf(offer.id)

        self.assertIn(customer_last_name, pdf.format_file_name())

    def test_get_template_returns_template(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX)

        pdf = ProcessPdf(offer.id)
        pdf_template = pdf.get_template(offer)
        self.assertEqual(pdf_template.filename, 'tx_resale_non_condo.pdf')

    def test_get_template_errors_when_template_not_found(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, 'ID')

        with self.assertRaises(Exception, msg='Contract template not found'):
            ProcessPdf(offer.id)

    def test_contract_data_function(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX)
        pdf = ProcessPdf(offer.id)
        pdf.tx_contract_data = MagicMock(return_value=1)
        pdf.contract_data()
        pdf.tx_contract_data.assert_called()

    def test_contract_data_function_calls_ga_contract_data(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.GA)
        pdf = ProcessPdf(offer.id)
        pdf.ga_contract_data = MagicMock(return_value=3)
        pdf.contract_data()
        pdf.ga_contract_data.assert_called_once()

    def test_get_tx_contract_data(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX)

        pdf = ProcessPdf(offer.id)

        contract_data = pdf.tx_contract_data()
        expected_inline_address = '3211 Test Rd., Austin, TX, 78704'
        expected_offer_price = '500,000.00'
        self.assertEqual(contract_data['property_street'], '3211 Test Rd. 78704')
        self.assertEqual(contract_data['property_city'], 'Austin')
        self.assertEqual(contract_data['sales_price_cash_portion'], expected_offer_price)
        self.assertEqual(contract_data['sales_price'], expected_offer_price)
        self.assertEqual(contract_data['yes_hoa'], True)
        self.assertEqual(contract_data['no_hoa'], None)
        self.assertEqual(contract_data['close_date'], 'May 26')
        self.assertEqual(contract_data['close_year'], '21')
        self.assertEqual(contract_data['addendum_property_address'], expected_inline_address)
        self.assertEqual(contract_data['abad_property_address'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_two'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_three'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_four'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_five'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_six'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_seven'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_eight'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_nine'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_ten'], expected_inline_address)
        self.assertEqual(contract_data['offer_property_address_eleven'], expected_inline_address)

    def test_get_ga_contract_data(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.GA, 1968, 'BAWAG')
        offer.finance_approved_close_date = datetime.strptime("2021-08-26", "%Y-%m-%d")
        offer.save()
        pdf = ProcessPdf(offer.id)

        contract_data = pdf.ga_contract_data()
        self.assertEqual(contract_data['property_street'], '3211 Test Rd. 78704')
        self.assertEqual(contract_data['property_street_and_city'], '3211 Test Rd. Austin')
        self.assertEqual(contract_data['property_street_and_city_2'], '3211 Test Rd. Austin')
        self.assertEqual(contract_data['property_city'], 'Austin')
        self.assertEqual(contract_data['property_zip_1'], '78704')
        self.assertEqual(contract_data['property_zip_2'], '78704')
        self.assertEqual(contract_data['property_zip_3'], '78704')
        self.assertEqual(contract_data['sales_price'], '500,000.00')
        self.assertEqual(contract_data['built_before_1978'], True)
        self.assertEqual(contract_data['sellers_broker'], 'Jimmy Drake Realty')
        self.assertEqual(contract_data['not_built_before_1978'], None)
        self.assertEqual(contract_data['has_lead_based_paint'], True)
        self.assertEqual(contract_data['buyer_name'], 'Purchasing Fund 2020-1, LLC')
        self.assertEqual(contract_data['addendum_property_address'], '3211 Test Rd., Austin, GA, 78704')
        self.assertEqual(contract_data['property_mls'], '6230076')
        self.assertEqual(contract_data['close_date'], 'August 26, 2021')

    def test_build_date_is_before_1978(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX, 1968)
        pdf = ProcessPdf(offer.id)
        self.assertEqual(pdf._is_built_before(1978, offer.year_built), True)

    def test_build_date_is_not_before_1978(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX, 1992)
        pdf = ProcessPdf(offer.id)
        self.assertEqual(pdf._is_built_before(1978, offer.year_built), False)

    def test_build_date_is_none(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX, None)
        pdf = ProcessPdf(offer.id)
        self.assertEqual(pdf._is_built_before(1978, offer.year_built), None)

    def test_get_buyer_name_when_funding_type_is_BAWAG(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX, 1968, 'BAWAG')
        pdf = ProcessPdf(offer.id)
        self.assertEqual(pdf._get_buyer_name(offer.funding_type), 'Purchasing Fund 2020-1, LLC')

    def test_get_buyer_name_when_funding_type_is_Quanta(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX, 1968, 'Quanta')
        offer.funding_type = 'Quanta'
        pdf = ProcessPdf(offer.id)
        self.assertEqual(pdf._get_buyer_name(offer.funding_type), 'Purchasing Fund 2019-3, LLC')

    def test_get_buyer_name_when_funding_type_is_none(self):
        offer = self.create_pdf_offer(ContractType.RESALE, PropertyType.SINGLE_FAMILY, BuyingState.TX, 1968, None)
        offer.funding_type = None
        pdf = ProcessPdf(offer.id)
        self.assertEqual(pdf._get_buyer_name(offer.funding_type), None)
