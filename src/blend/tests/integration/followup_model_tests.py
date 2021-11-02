from unittest.mock import call, patch

from rest_framework.test import APITestCase

from application.models.application import Application
from application.models.loan import Loan
from application.tests import random_objects
from application.tests.random_objects import fake

from blend.models import Followup


class FollowupModelTests(APITestCase): 

    def setUp(self) -> None:
        self.application = random_objects.random_application(new_salesforce=fake.pystr(max_chars=18))
        self.loan = random_objects.random_loan(blend_application_id='69af5d15-22a4-4052-96d3-c526339532e0', application=self.application, salesforce_id=fake.pystr(max_chars=18))
        self.followup = random_objects.random_followup(blend_followup_id='7254aeb7-898b-4aae-bfbc-df86dc861635', blend_application_id='69af5d15-22a4-4052-96d3-c526339532e0', application=self.application, loan=self.loan)

    @patch("blend.models.homeward_salesforce")
    def test_converting_to_salesforce_payload(self, hw_sf_patch):
        hw_sf_patch.create_new_salesforce_object.return_value = random_objects.fake.pystr(max_chars=18)
        actual_payload = self.followup.salesforce_field_mapping()

        self.assertEqual(actual_payload['Type__c'], self.followup.followup_type)
        self.assertEqual(actual_payload['Status__c'], self.followup.status)
        self.assertEqual(actual_payload['Description__c'], self.followup.description)
        self.assertEqual(actual_payload['Requested_Date__c'], self.followup.requested_date.strftime("%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(actual_payload['Loan_Application__c'], self.loan.salesforce_id)
        self.assertEqual(actual_payload['Blend_Application_Id__c'], self.followup.blend_application_id)
        self.assertEqual(actual_payload['Blend_Followup_Id__c'], self.followup.blend_followup_id) #this field needs to be added to the salesforce model 
    
    @patch("blend.models.homeward_salesforce.create_new_salesforce_object")
    def test_push_to_salesforce(self, push_to_salesforce_patch):
        push_to_salesforce_patch.create_new_salesforce_object.return_value = random_objects.fake.pystr(max_chars=18)

        push_to_salesforce_patch.create_new_salesforce_object(self.followup.to_salesforce_representation(), self.followup.salesforce_object_type)
        create_call = [call.create_new_salesforce_object(self.followup.to_salesforce_representation(), self.followup.salesforce_object_type)]
        push_to_salesforce_patch.assert_has_calls(create_call)
    

    @patch("blend.models.homeward_salesforce.update_salesforce_object")
    def test_should_update_salesforce_followup_when_sf_id_present(self, update_sf_object_patch):
        self.followup.salesforce_id = random_objects.fake.pystr(max_chars=18)
        self.followup.save()

        update_sf_object_patch.update_salesforce_object(self.followup.salesforce_id, self.followup.to_salesforce_representation(), self.followup.salesforce_object_type)
        update_call = [call.update_salesforce_object(self.followup.salesforce_id, self.followup.to_salesforce_representation(), self.followup.salesforce_object_type)]
        update_sf_object_patch.assert_has_calls(update_call)
    
    @patch("blend.models.Followup.attempt_push_to_salesforce", side_effect=Exception('ENTITY_IS_DELETED'))
    def test_attempt_push_to_sf_raises_exception_when_entity_is_deleted(self, push_to_sf_patch):
        with self.assertRaises(Exception, msg='ENTITY_IS_DELETED'):
            self.followup.save()
        
    @patch("blend.models.Followup.attempt_push_to_salesforce", side_effect=Exception('INVALID_FIELD'))  
    def test_attempt_push_to_sf_raises_exception_when_invalid_field(self, push_to_sf_patch):
        with self.assertRaises(Exception, msg='INVALID_FIELD'):
            self.followup.save()
    
    @patch("blend.models.Followup.attempt_push_to_salesforce", side_effect=Exception('UNKNOWN_EXCEPTION'))  
    def test_attempt_push_to_sf_raises_exception_when_unknown_exception(self, push_to_sf_patch):
        with self.assertRaises(Exception, msg='UNKNOWN_EXCEPTION'):
            self.followup.save()
    
    @patch("blend.models.Followup.attempt_push_to_salesforce", side_effect=[Exception('UNKNOWN_EXCEPTION'), Exception('UNKNOWN_EXCEPTION')])  
    def test_attempt_push_to_sf_retries_when_unknown_exception_is_raised(self, push_to_sf_patch):
        with self.assertRaises(Exception, msg='UNKNOWN_EXCEPTION'):
            self.followup.save()
            self.assertEqual(push_to_sf_patch.call_count, 2)
    
    @patch("blend.models.Followup.attempt_push_to_salesforce", side_effect=OSError)  
    def test_attempt_push_to_sf_raises_os_error_if_os_error(self, push_to_sf_patch):
        with self.assertRaises(OSError):
            self.followup.save()
    
    @patch("blend.models.Followup.attempt_push_to_salesforce", side_effect=[OSError, OSError])
    def test_attempt_push_to_sf_retries_when_os_error_raised(self, push_to_sf_patch):
        with self.assertRaises(OSError):
            self.followup.save()
            self.assertEqual(push_to_sf_patch.call_count, 2)  
    
    
