import logging

from django.db import models
from django.conf import settings
import time

from application.models.application import Application
from application.models.loan import Loan
from utils.models import CustomBaseModelMixin, anyof
from utils.salesforce import homeward_salesforce
from utils.salesforce_model_mixin import SalesforceModelMixin, SalesforceObjectType

logger = logging.getLogger(__name__)
max_retries = settings.BLEND.get('FOLLOWUP_SALESFORCE_RETRIES')

class Followup(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    TYPE = 'Type__c'
    STATUS = 'Status__c'
    DESCRIPTION = 'Description__c'
    REQUESTED_DATE = 'Requested_Date__c'
    LOAN_APPLICATION_ID = 'Loan_Application__c'
    BLEND_APPLICATION_ID = 'Blend_Application_Id__c'
    BLEND_FOLLOWUP_ID = 'Blend_Followup_Id__c'  # this field needs to be added to the salesforce model

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="followups")
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="followups")
    blend_application_id = models.TextField(blank=False, null=False)
    blend_followup_id = models.TextField(blank=False, null=False, unique=True)
    followup_type = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    requested_date = models.DateTimeField(blank=True, null=True)
    salesforce_id = models.TextField(blank=True, null=True, unique=True)

    salesforce_object_type = SalesforceObjectType.FOLLOWUP

    def salesforce_field_mapping(self):
        return {
            self.TYPE: self.followup_type,
            self.STATUS: self.status,
            self.DESCRIPTION: self.description,
            self.REQUESTED_DATE: self.requested_date.strftime("%Y-%m-%dT%H:%M:%S") if self.requested_date else None,
            self.LOAN_APPLICATION_ID: self.loan.salesforce_id,
            self.BLEND_APPLICATION_ID: self.blend_application_id,
            self.BLEND_FOLLOWUP_ID: self.blend_followup_id
        }

    def save(self, *args, **kwargs):
        self.attempt_push_to_salesforce(retries=0)
        super(Followup, self).save(*args, **kwargs)

    def attempt_push_to_salesforce(self, retries):
        salesforce_representation = self.to_salesforce_representation()
        try:
            if self.salesforce_id:
                homeward_salesforce.update_salesforce_object(self.salesforce_id, salesforce_representation,
                                                             self.salesforce_object_type)
            else:
                salesforce_id = homeward_salesforce.create_new_salesforce_object(salesforce_representation,
                                                                                 self.salesforce_object_type)
                self.salesforce_id = salesforce_id
        except Exception as e:
            self.handle_exception(retries, e)
        except OSError as e:
            self.handle_os_error(retries, e)
    
    def handle_exception(self, retries, error):
        max_retries_int = int(max_retries)
        
        if anyof(['ENTITY_IS_DELETED', 'INVALID_FIELD'], str(error.args)):
            message = f"Failed sending followup {self.id} to salesforce for loan {self.loan_id}"
            err_type = "sf_push_attempt_followup_send_failed_loan_not_found"
        elif anyof(['UNKNOWN_EXCEPTION'], str(error.args)):
            if retries < max_retries_int: 
                retries = retries + 1 
                time.sleep(retries)
                return self.attempt_push_to_salesforce(retries)
            else:
                message = f"Failed sending followup {self.id} to salesforce"
                err_type = "sf_push_attempt_followup_send_failed"
        else:
            message = f"Failed sending followup {self.id} to salesforce"
            err_type = "sf_push_attempt_followup_send_failed"
        
        logger.exception(message, exc_info=error, extra=dict(
                type=err_type,
                followup_id=self.id,
                loan_id=self.loan_id,
                salesforce_id=self.salesforce_id,
                salesforce_rep=self.to_salesforce_representation(),
                salesforce_obj_type=self.salesforce_object_type
        ))
    
    def handle_os_error(self, retries, error):
        max_retries_int = int(max_retries)
        if retries < max_retries_int: 
                retries = retries + 1 
                time.sleep(retries)
                return self.attempt_push_to_salesforce(retries)
        else:
            message = f"Failed sending followup {self.id} to salesforce"
            err_type = "sf_push_attempt_followup_send_failed"
            
        logger.exception(message, exc_info=error, extra=dict(
            type=err_type,
            followup_id=self.id,
            loan_id=self.loan_id,
            salesforce_id=self.salesforce_id,
            salesforce_rep=self.to_salesforce_representation(),
            salesforce_obj_type=self.salesforce_object_type
        ))
    