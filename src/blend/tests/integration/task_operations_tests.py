from unittest import mock
from django.test import TestCase
from unittest.mock import patch
import json 
from requests import Response

from application.models.application import Application
from application.models.loan import Loan
from blend.models import Followup
from application.tests import random_objects
from blend.task_operations import process_follow_up_data
from blend.tasks import poll_blend_api 
from blend.blend_api_client import get

def mocked_get_followups_without_proxies(type, url, headers, params):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return MockResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","applicationId":"69af5d15-22a4-4052-96d3-c526339532e0","type":"DOCUMENT_REQUEST","status":"PENDING_REVIEW","requestedAt":"2021-02-26T23:50:02.485Z","requestedBy":"dc0f335b-3b69-45b3-82e6-f635c4c24407","completedAt":"2021-02-26T23:51:22.864Z","comments":"Credit Report -- Lender to obtain a satisfactory credit report.","context":{"partyId":"8d6524b1-fcf3-4fea-b132-e8d2b6721e4e","document":{"type":"CREDIT_REPORT","title":"Credit Report","id":"fc57efa6-57c5-40d1-a8fa-9106139bf7a8"}}}]}', 200)

def mocked_get_followup_that_changed(type, url, headers, params):
    class AnotherMockedResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return AnotherMockedResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","applicationId":"69af5d15-22a4-4052-96d3-c526339532e0","type":"DOCUMENT_REQUEST","status":"APPROVED","requestedAt":"2021-02-26T23:50:02.485Z","requestedBy":"dc0f335b-3b69-45b3-82e6-f635c4c24407","completedAt":"2021-02-26T23:51:22.864Z","comments":"Credit Report -- Lender to obtain a satisfactory credit report.","context":{"partyId":"8d6524b1-fcf3-4fea-b132-e8d2b6721e4e","document":{"type":"CREDIT_REPORT","title":"Credit Report","id":"fc57efa6-57c5-40d1-a8fa-9106139bf7a8"}}}]}', 200)

def mocked_get_followup_failed(type, url, headers, params):
    class FailedMockedResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return FailedMockedResponse(None, 500)
#is there a better way to do lines 48-101
def mock_system_followup_types(type, url, headers, params):
    class SystemMockedResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return SystemMockedResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","status":"APPROVED","requestedAt":"2021-02-26T23:50:02.485Z", "type": "SYSTEM", "applicationId":"69af5d15-22a4-4052-96d3-c526339532e0", "context":{"description":"testdescription", "taxReturnYear":"2020", "w2Year":"2020", "document":{"type":"CREDIT_REPORT","title":"Credit Report"}}}]}', 200)

def mock_paystubs_followup_types(type, url, headers, params):
    class PaystubsMockedResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return PaystubsMockedResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","status":"APPROVED","requestedAt":"2021-02-26T23:50:02.485Z", "type": "PAYSTUBS", "applicationId":"69af5d15-22a4-4052-96d3-c526339532e0", "context":{"description":"testdescription", "taxReturnYear":"2020", "w2Year":"2020", "document":{"type":"CREDIT_REPORT","title":"Credit Report"}}}]}', 200)

def mock_tax_return_followup_types(type, url, headers, params):
    class TaxReturnMockedResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return TaxReturnMockedResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","status":"APPROVED","requestedAt":"2021-02-26T23:50:02.485Z", "type": "TAX_RETURN", "applicationId":"69af5d15-22a4-4052-96d3-c526339532e0", "context":{"description":"testdescription", "taxReturnYear":"2020", "w2Year":"2020", "document":{"type":"CREDIT_REPORT","title":"Credit Report"}}}]}', 200)

def mock_w2_followup_types(type, url, headers, params):
    class W2MockedResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return W2MockedResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","status":"APPROVED","requestedAt":"2021-02-26T23:50:02.485Z", "type": "W2", "applicationId":"69af5d15-22a4-4052-96d3-c526339532e0", "context":{"description":"testdescription", "taxReturnYear":"2020", "w2Year":"2020", "document":{"type":"CREDIT_REPORT","title":"Credit Report"}}}]}', 200)

def mock_document_request_followup_types(type, url, headers, params):
    class DocumentRequestResponse:
        def __init__(self, json_data, status_code):
            self.content = json_data
            self.json_data = json_data
            self.status_code = status_code
            self.reason = None

        def json(self):
            return self.json_data
    
    return DocumentRequestResponse('{"followUps":[{"id":"7254aeb7-898b-4aae-bfbc-df86dc861635","status":"APPROVED","requestedAt":"2021-02-26T23:50:02.485Z", "type": "DOCUMENT_REQUEST", "applicationId":"69af5d15-22a4-4052-96d3-c526339532e0", "context":{"description":"testdescription", "taxReturnYear":"2020", "w2Year":"2020", "document":{"type":"CREDIT_REPORT","title":"Credit Report"}}}]}', 200)


class TaskOperationsTests(TestCase):
    def setUp(self):
        self.complete_application = random_objects.random_application(stage="complete")
        self.denied_application = random_objects.random_application(stage="denied")
        self.loan = random_objects.random_loan(application=self.complete_application)
        self.loan.status = 'Application completed'
        self.loan.save()

    @patch('requests.request', side_effect=mocked_get_followups_without_proxies)
    def test_should_create_a_new_followup_if_followup_doesnot_exist(self, mock_get):
        followups_count = Followup.objects.all().count()
        poll_blend_api()
        self.assertEqual(Followup.objects.all().count(), followups_count + 1)

    @patch('requests.request', side_effect=mocked_get_followup_that_changed)
    def test_should_update_a_followup_if_followup_exists(self, mock_get):
        followup = random_objects.random_followup(application=self.complete_application, loan=self.loan, blend_followup_id='7254aeb7-898b-4aae-bfbc-df86dc861635')
        followups_count = Followup.objects.all().count()
        poll_blend_api()

        self.assertEqual(Followup.objects.all().count(), followups_count)
        self.assertEqual(followup.status, None)

        
    @patch('blend.task_operations.process_follow_up_data')
    @patch('requests.request', side_effect=mocked_get_followup_that_changed)
    def test_should_break_out_of_loop_if_500(self, process_follow_up_data_patch, mock_get):
        poll_blend_api()
        process_follow_up_data_patch.assert_called_once()
    

    @patch('requests.request', side_effect=mock_system_followup_types)
    def test_should_set_description_based_on_followup_type(self, mock_get):
        followup = random_objects.random_followup(application=self.complete_application, loan=self.loan)
        followup.blend_followup_id = '7254aeb7-898b-4aae-bfbc-df86dc861635'
    
        followup.save()

        poll_blend_api()
        followup.refresh_from_db()
        self.assertEqual(followup.description, "testdescription")

    @patch('requests.request', side_effect=mock_paystubs_followup_types)
    def test_should_default_description_if_type_is_paystubs(self, mock_get): 
        followup = random_objects.random_followup(application=self.complete_application, loan=self.loan)
        followup.blend_followup_id = '7254aeb7-898b-4aae-bfbc-df86dc861635'
    
        followup.save()

        poll_blend_api()
        followup.refresh_from_db()
        self.assertEqual(followup.description, "Paystubs")

    @patch('requests.request', side_effect=mock_tax_return_followup_types)
    def test_should_pull_description_contexttaxreturn_if_type_is_paystubs(self, mock_get): 
        followup = random_objects.random_followup(application=self.complete_application, loan=self.loan)
        followup.blend_followup_id = '7254aeb7-898b-4aae-bfbc-df86dc861635'
    
        followup.save()

        poll_blend_api()
        followup.refresh_from_db()
        self.assertEqual(followup.description, "2020")

    @patch('requests.request', side_effect=mock_w2_followup_types)
    def test_should_pull_description_from_context_year_if_type_is_w2(self, mock_get):
        followup = random_objects.random_followup(application=self.complete_application, loan=self.loan)
        followup.blend_followup_id = '7254aeb7-898b-4aae-bfbc-df86dc861635'
    
        followup.save()

        poll_blend_api()
        followup.refresh_from_db()
        self.assertEqual(followup.description, "2020")

    @patch('requests.request', side_effect=mock_document_request_followup_types)
    def test_should_pull_description_from_document_title_if_document_request(self, mock_get):
        followup = random_objects.random_followup(application=self.complete_application, loan=self.loan)
        followup.blend_followup_id = '7254aeb7-898b-4aae-bfbc-df86dc861635'
    
        followup.save()

        poll_blend_api()
        followup.refresh_from_db()
        self.assertEqual(followup.description, "Credit Report")

