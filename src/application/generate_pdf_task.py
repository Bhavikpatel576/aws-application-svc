import locale
import logging
import os
import os.path
from datetime import datetime
from pathlib import Path

import pdfrw

from application.models.contract_template import ContractTemplate, BuyingState
from application.models.offer import Offer
from utils.aws import retrieve_contract_template, upload_homeward_contract

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, '')
SUPPORTED_STATES = {
    'Tx': 'TX',
    'Ga': 'GA'
}


class ProcessPdf:

    def __init__(self, offer_id):
        offer = Offer.objects.get(id=offer_id)
        # If template exists and is active we will try to pre-fill it
        self.contract_template = self.get_template(offer)
        self.offer = offer
        self.temp_directory = str(Path(__file__).parent) + "/tmp/"
        self.output_file = self.format_file_name()

    def format_file_name(self):
        return self.offer.application.customer.name.split(" ")[-1] + "_" + datetime.now().strftime(
            "%Y_%m_%d_%H_%M_%S") + ".pdf"

    def format_address_string(self, inline_address_string):
        address_first_letter_capitalized = inline_address_string.title()
        for key in SUPPORTED_STATES:
            correct_address_capitalization = address_first_letter_capitalized.replace(key, SUPPORTED_STATES[key])

        return correct_address_capitalization

    def add_data_to_pdf(self):
        data = self.contract_data()
        template_filename = self.contract_template.filename
        downloaded_contract = retrieve_contract_template(template_filename)
        template = pdfrw.PdfReader(downloaded_contract)
        file_path = self.temp_directory + self.output_file
        for page in template.pages:
            annotations = page['/Annots']
            if annotations is None:
                continue
            self.populate_annotations(annotations, data)

        template.Root.AcroForm.update(pdfrw.PdfDict(NeedAppearances=pdfrw.PdfObject('true')))
        pdfrw.PdfWriter().write(file_path, template)

        s3_url = upload_homeward_contract(file_path, self.offer.id, self.output_file)
        return s3_url

    def populate_annotations(self, page_annotations, data):
        for annotation in page_annotations:
            # Skip annotations where annotation['/T'] is None
            # This allows PDF to still be filled out if annotations are bad
            try:
                key = annotation['/T'][1:-1]
            except TypeError:
                continue
            if key in data:
                value = data[key]
                if "property_address" in key:
                    annotation.update(self.encode_pdf_address_string(value))
                else:
                    annotation.update(self.encode_pdf_string(value))
                annotation.update(pdfrw.PdfDict(AP=''))

    def encode_pdf_string(self, value):
        if isinstance(value, str):
            if value:
                return pdfrw.PdfDict(V=pdfrw.objects.pdfstring.PdfString.encode(value.title()))
            else:
                return pdfrw.PdfDict(V=pdfrw.objects.pdfstring.PdfString.encode(''))
        elif isinstance(value, bool):
            if value:
                return pdfrw.PdfDict(AS=pdfrw.objects.pdfname.BasePdfName('/Yes'),
                                     V=pdfrw.objects.pdfname.BasePdfName('/Yes'))
            else:
                return pdfrw.PdfDict(AS=pdfrw.objects.pdfname.BasePdfName('/No'),
                                     V=pdfrw.objects.pdfname.BasePdfName('/No'))
        return ''

    def encode_pdf_address_string(self, value):
        if isinstance(value, str):
            if value:
                inline_address_value = self.format_address_string(value)
                return pdfrw.PdfDict(V=pdfrw.objects.pdfstring.PdfString.encode(inline_address_value))
            else:
                return pdfrw.PdfDict(V=pdfrw.objects.pdfstring.PdfString.encode(''))

    def delete_temp_files(self):
        path = self.temp_directory + self.output_file
        try:
            os.remove(path)
        except Exception as e:
            logger.exception("Exception raised while deleting the temp file in ProcessPdf", exc_info=e, extra=dict(
                type="exception_during_temp_file_delete",
                path=path,
                temp_directory=self.temp_directory,
                output_file=self.output_file
            ))

    def get_template(self, offer: Offer):
        if offer.offer_property_address:
            state = offer.offer_property_address.state
        else:
            logger.error(f"Offer {offer.id} is missing a property address", extra=dict(
                type="offer_missing_property_address_for_get_template",
                offer_id=offer.id
            ))
            raise ValueError(f'Offer {offer.id} is missing a property address.')

        try:
            contract_template = ContractTemplate.objects.get(active=True, buying_state=state,
                                                             property_type=offer.property_type,
                                                             contract_type=offer.contract_type)
        except ContractTemplate.DoesNotExist as e:
            logger.exception("Contract template not found", exc_info=e, extra=dict(
                type="contact_template_not_found",
                buying_state=state,
                property_type=offer.property_type,
                contract_type=offer.contract_type
            ))
            raise Exception('Contract template not found.')
        return contract_template

    def contract_data(self):
        if self.contract_template.buying_state == BuyingState.TX:
            return self.tx_contract_data()
        elif self.contract_template.buying_state == BuyingState.GA:
            return self.ga_contract_data()

    def tx_contract_data(self):
        inline_address = self.offer.offer_property_address.get_inline_address()
        return {
            "property_street": self.offer.offer_property_address.street_and_zip_address(),
            "property_city": self.offer.offer_property_address.city,
            "sales_price_cash_portion": "{:,}".format(self.offer.offer_price),
            "sales_price": "{:,}".format(self.offer.offer_price),
            "earnest_deliver_to_name": "Homeward Title",
            "termination_days": None,
            "yes_hoa": True if self.offer.hoa else None,
            "no_hoa": True if self.offer.hoa is False else None,
            "close_date": self.offer.preferred_closing_date.strftime(
                "%B %d") if self.offer.preferred_closing_date else None,
            "close_year": self.offer.preferred_closing_date.strftime(
                "%y") if self.offer.preferred_closing_date else None,
            "addendum_property_address": inline_address,
            "abad_property_address": inline_address,
            "offer_property_address": inline_address,
            "offer_property_address_two": inline_address,
            "offer_property_address_three": inline_address,
            "offer_property_address_four": inline_address,
            "offer_property_address_five": inline_address,
            "offer_property_address_six": inline_address,
            "offer_property_address_seven": inline_address,
            "offer_property_address_eight": inline_address,
            "offer_property_address_nine": inline_address,
            "offer_property_address_ten": inline_address,
            "offer_property_address_eleven": inline_address,
            "other_agreement_list": "Homeward Title Affiliated Business Disclosure"
        }

    def ga_contract_data(self):
        inline_address = self.offer.offer_property_address.get_inline_address()
        built_before_1978 = self._is_built_before(1978, self.offer.year_built)
        not_built_before_1978 = True if built_before_1978 is False else None
        has_lead_based_paint = True if built_before_1978 is True else None
        buyer_name = self._get_buyer_name(self.offer.funding_type)
        seller_broker = self.offer.office_name if self.offer.office_name is not None else None
        property_mls = self.offer.mls_listing_id if self.offer.mls_listing_id is not None else None
        close_date = self.offer.finance_approved_close_date.strftime(
            "%B %d, %Y") if self.offer.finance_approved_close_date else None

        return {
            "property_street": self.offer.offer_property_address.street_and_zip_address(),
            "property_street_and_city": self.offer.offer_property_address.street_and_city_address(),
            "property_street_and_city_2": self.offer.offer_property_address.street_and_city_address(),
            "property_city": self.offer.offer_property_address.city,
            "property_zip_1": self.offer.offer_property_address.zip,
            "property_zip_2": self.offer.offer_property_address.zip,
            "property_zip_3": self.offer.offer_property_address.zip,
            "sales_price": "{:,}".format(self.offer.offer_price),
            "built_before_1978": built_before_1978,
            "sellers_broker": seller_broker,
            "not_built_before_1978": not_built_before_1978,
            "has_lead_based_paint": has_lead_based_paint,
            "buyer_name": buyer_name,
            "addendum_property_address": inline_address,
            "property_mls": property_mls,
            "close_date": close_date
        }

    def _is_built_before(self, comparison_year: int, year_built):
        if year_built:
            return comparison_year > year_built

        return None

    def _get_buyer_name(self, funding_type: str):
        if funding_type == 'BAWAG':
            return 'Purchasing Fund 2020-1, LLC'
        elif funding_type == 'Quanta':
            return 'Purchasing Fund 2019-3, LLC'

        return None
