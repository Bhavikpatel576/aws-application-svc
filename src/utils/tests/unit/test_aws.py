import botocore.session
from botocore.stub import Stubber

from django.test import SimpleTestCase

from utils import aws

TEMPLATE_NAME = 'test_this_template.pdf'


class ContractTemplateRetrievalTests(SimpleTestCase):

    def test_converts_s3_client_error(self):
        s3 = botocore.session.get_session().create_client('s3')
        stubber = Stubber(s3)
        stubber.add_client_error('get_object', 'NoSuchKey')
        stubber.activate()

        with self.assertRaises(ValueError):
            aws.retrieve_contract_template(TEMPLATE_NAME, s3)
