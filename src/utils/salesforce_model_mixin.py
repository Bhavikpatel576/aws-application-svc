import abc
from enum import Enum


class SalesforceObjectType(str, Enum):
    ACCOUNT = "Account"
    OLD_HOME = "Old_Home__c"
    OFFER = "Offer__c"
    FOLLOWUP = "Blend_Follow_Up__c"

class SalesforceModelException(Exception):
    pass


class SalesforceModelMixin:
    @abc.abstractmethod
    def salesforce_field_mapping(self):
        pass

    @abc.abstractmethod
    def salesforce_object_type(self) -> SalesforceObjectType:
        pass

    def map_if_field_is_present(self, application_field, person_data, salesforce_field_to_map_to,
                                transform_function=lambda arg: arg):
        if application_field:
            person_data.update({salesforce_field_to_map_to: transform_function(application_field)})

    def to_salesforce_representation(self, mapping=None):
        payload = {}
        if not mapping:
            mapping = self.salesforce_field_mapping()
        for k, v in mapping.items():
            if isinstance(v, bool):
                payload.update({k: v})
            elif not isinstance(v, str):
                self.map_if_field_is_present(v, payload, k, str)
            else:
                self.map_if_field_is_present(v, payload, k)
        return payload
