
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import ANY, call, patch

from rest_framework.test import APITestCase

from application.models.application import Application
from application.models.current_home import CurrentHome
from application.tasks import push_to_salesforce
from application.tests import random_objects
from user.models import User
from utils.salesforce_model_mixin import SalesforceObjectType


@patch("utils.salesforce.homeward_salesforce.get_id_by_email")
@patch("utils.salesforce.homeward_salesforce.get_current_home_id_by_account_id")
@patch("utils.salesforce.homeward_salesforce.update_salesforce_object")
@patch("utils.salesforce.homeward_salesforce.create_new_salesforce_object")
class PushToSalesforceTests(APITestCase):
    module_dir = str(Path(__file__).parent)
    fixtures = [os.path.join(module_dir, "../static/filled_app_salesforce_test.json")]

    def should_not_attempt_to_push_user_when_no_app(self, create_mock, update_mock, get_current_home_id_mock, get_id_mock):
        create_mock.assert_not_called()
        user = User.objects.get(pk=1)
        user.email="notacustomer@test.com"
        user.save()
        update_mock.assert_not_called()

    def test_should_push_user_login_data_to_salesforce_when_user_updated(self, create_mock, update_mock, get_current_home_id_mock, get_id_mock):
        create_mock.assert_not_called()
        app = Application.objects.get(pk="aca30e9e-776b-44fb-ba37-93e4b195cefe")
        user = User.objects.get(pk=1)
        app.new_salesforce = None
        app.save()
        last_login = datetime.now()
        user.last_login = last_login
        user.save()
        update_mock.assert_not_called()
        app.new_salesforce="some-sf-id-value"
        app.save()
        last_login = datetime.now()
        user.last_login = last_login
        user.save()
        update_mock.assert_called_once_with("some-sf-id-value", {'First_Application_Log_In__c': str(user.date_joined.strftime("%Y-%m-%dT%H:%M:%S")),
                                                                 'Last_Application_Log_In__c': user.last_login.strftime("%Y-%m-%dT%H:%M:%S")},
                                            SalesforceObjectType.ACCOUNT)

    def test_only_sync_acct_if_no_current_home(self, create_mock, update_mock, get_current_home_id_mock, get_id_mock):
        app = random_objects.random_application()
        get_id_mock.return_value = "person_id-123"
        push_to_salesforce(app.id)
        get_current_home_id_mock.assert_not_called()
        update_mock.assert_called_once_with("person_id-123", ANY, SalesforceObjectType.ACCOUNT)

    def test_should_make_correct_sf_calls(self, create_mock, update_mock, get_current_home_id_mock, get_id_mock):
        current_home = CurrentHome.objects.get(pk="74d75877-fefc-40cd-8479-7c2008eb7774")
        payload = current_home.to_salesforce_representation()
        app = random_objects.random_application(current_home=current_home)
        get_id_mock.return_value = "person_id-123"
        get_current_home_id_mock.return_value = "current_home_id-123"
        # should get current home sf id if we dont' already have one and update both objects
        push_to_salesforce(app.id)
        get_current_home_id_mock.assert_called_once()
        update_calls = [call("person_id-123", ANY, SalesforceObjectType.ACCOUNT), call("current_home_id-123", ANY, SalesforceObjectType.OLD_HOME)]
        update_mock.assert_has_calls(update_calls)
        current_home.refresh_from_db()
        # should also save new current home id to current home
        self.assertEqual("current_home_id-123", current_home.salesforce_id)

        # if we do, skip get current home id
        get_current_home_id_mock.reset_mock()
        push_to_salesforce(app.id)
        get_current_home_id_mock.assert_not_called()

        # should create both objects when no ids exist
        update_mock.reset_mock()
        get_id_mock.reset_mock()
        get_current_home_id_mock.reset_mock()
        get_current_home_id_mock.return_value = None
        get_id_mock.return_value = None
        create_mock.side_effect = ["new_person_id", "new_old_home_id"]
        current_home.salesforce_id = None
        current_home.save()
        push_to_salesforce(app.id)
        create_calls = [call(data=ANY, object_type=SalesforceObjectType.ACCOUNT), call(data=ANY, object_type=SalesforceObjectType.OLD_HOME)]
        create_mock.assert_has_calls(create_calls)
        current_home.refresh_from_db()
        self.assertEqual(current_home.salesforce_id, "new_old_home_id")
        get_current_home_id_mock.assert_called_once_with(account_id="new_person_id")
  