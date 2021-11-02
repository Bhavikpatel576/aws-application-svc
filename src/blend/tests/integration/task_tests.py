from django.test import TestCase
from rest_framework.test import APITestCase
from unittest.mock import patch
import json 


from application.models.application import Application
from application.models.loan import Loan
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


class TaskTests(TestCase): 

    def setUp(self):
        self.complete_application = random_objects.random_application(stage="complete")
        self.withdrawn_application = random_objects.random_application(stage="complete", mortgage_status="Withdrawn - Incomplete")
        self.denied_application = random_objects.random_application(stage="denied")
        self.loan = random_objects.random_loan(application=self.complete_application)
        self.loan.status = 'Application completed'
        self.loan.save()

    @patch('blend.task_operations.process_follow_up_data')
    @patch('requests.request', side_effect=mocked_get_followups_without_proxies)
    def test_poll_blend_api(self, process_follow_up_data_patch, mock_get):
        poll_blend_api()

        process_follow_up_data_patch.assert_called_once()