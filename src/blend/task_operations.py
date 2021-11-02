import logging
import json
import dateutil.parser

from blend import blend_api_client
from blend.blend_api_client import BlendClientException
from blend.models import Followup
from django.conf import settings

logger = logging.getLogger(__name__)


def process_follow_up_data(loan_apps):
    url = settings.BLEND.get('BASE_URL') + '/follow-ups'
    for loan_app in loan_apps:
        query_string = {"applicationId": loan_app.blend_application_id}
        response = blend_api_client.get(url, query_string, 0)

        if response.status_code == 200:
            create_or_update_follow_up(response.content, loan_app)
            logger.debug("Success response from blend API client for process follow up data", extra=dict(
                type="success_response_blend_process_follow_up_data",
                loan_app_id=loan_app.id,
                blend_application_id=loan_app.blend_application_id
            ))
            continue
        elif response.status_code == 404:
            logger.info("Not found received for blend API client process follow up data", extra=dict(
                type="404_for_blend_process_follow_up_data",
                loan_app_id=loan_app.id,
                blend_application_id=loan_app.blend_application_id
            ))
            continue
        else:
            logger.info("Invalid response received for blend API client process follow up data", extra=dict(
                type="invalid_for_blend_process_follow_up_data",
                loan_app_id=loan_app.id,
                blend_application_id=loan_app.blend_application_id,
                status_code=response.status_code,
                response=response.json(),
                reason=response.reason
            ))
            continue


def create_or_update_follow_up(response, loan_application):
    response_data = json.loads(response)
    for followup in response_data['followUps']:
        datetime_date = dateutil.parser.parse(followup['requestedAt'])
        defaults = {
            'application_id': loan_application.application_id,
            'loan_id': loan_application.id,
            'blend_application_id': followup['applicationId'],
            'followup_type': followup['type'],
            'status': followup['status'],
            'description': get_description(followup['type'], followup),
            'requested_date': datetime_date
        }
        try:
            Followup.objects.update_or_create(blend_followup_id=followup['id'], defaults=defaults)
        except Exception:
            pass


def get_description(followup_type, followup_data):
    if followup_type == 'SYSTEM':
        return followup_data['context']['description']
    elif followup_type == 'PAYSTUBS':
        return 'Paystubs'
    elif followup_type == 'TAX_RETURN':
        return followup_data['context']['taxReturnYear']
    elif followup_type == 'W2':
        return followup_data['context']['w2Year']
    elif followup_type == 'DOCUMENT_REQUEST':
        return followup_data['context']['document']['title']
