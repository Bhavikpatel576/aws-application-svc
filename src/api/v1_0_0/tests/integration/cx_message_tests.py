from unittest.mock import patch

from rest_framework.test import APITestCase
from rest_framework.response import Response

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import Application
from application.models.customer import Customer
from application.models.internal_support_user import InternalSupportUser


class CXMessageTests(AuthMixin, APITestCase):
    @patch("utils.hubspot.send_cx_manager_message")
    def test_post_cx_message(self, hubspot):
        sf_id = "321SOMEID123"
        url = '/api/1.0.0/message/'
        token = self.create_and_login_user('fakeloginuser')
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        hubspot.return_value = Response(status=200)

        customer = Customer.objects.create(email=user_email, name="Some Name")
        app = Application.objects.create(customer=customer, new_salesforce=sf_id)
        app.cx_manager = InternalSupportUser.objects.create(email="somecx@homeward.com")
        app.save()

        data = {
            "body": "asddfasdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf",
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.post(url, data, **headers, format='json')

        self.assertEqual(resp.status_code, 200)
        hubspot.assert_called_with(app.cx_manager.email, data.get('body'), app.customer.name,
                                   app.customer.email, "https://homewardinc--hwtest2.my.salesforce.com/lightning/r/Account/{}/view".format(sf_id))

    @patch("utils.hubspot.send_cx_manager_message")
    def test_post_cx_message_no_sf_id(self, hubspot):
        url = '/api/1.0.0/message/'
        token = self.create_and_login_user('fakeloginuser')
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        hubspot.return_value = Response(status=200)

        customer = Customer.objects.create(email=user_email, name="Some Name")
        app = Application.objects.create(customer=customer)
        app.cx_manager = InternalSupportUser.objects.create(email="somecx@homeward.com")
        app.save()

        data = {
            "body": "asddfasdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf",
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.post(url, data, **headers, format='json')

        self.assertEqual(resp.status_code, 200)
        hubspot.assert_called_with(app.cx_manager.email, data.get('body'), app.customer.name,
                                   app.customer.email, None)

    @patch("utils.hubspot.send_cx_manager_message")
    def test_should_422_when_no_cx(self, hubspot):
        sf_id = "321SOMEID123"
        url = '/api/1.0.0/message/'
        token = self.create_and_login_user('fakeloginuser')
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        hubspot.return_value = Response(status=200)

        customer = Customer.objects.create(email=user_email, name="Some Name")
        app = Application.objects.create(customer=customer, new_salesforce=sf_id)

        data = {
            "body": "asddfasdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf",
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.post(url, data, **headers, format='json')

        self.assertEqual(resp.status_code, 422)
        hubspot.assert_not_called()

    @patch("utils.hubspot.send_cx_manager_message")
    def test_should_return_400_when_no_message(self, hubspot):
        sf_id = "321SOMEID123"
        url = '/api/1.0.0/message/'
        token = self.create_and_login_user('fakeloginuser')
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        hubspot.return_value = Response(status=200)

        customer = Customer.objects.create(email=user_email, name="Some Name")
        app = Application.objects.create(customer=customer, new_salesforce=sf_id)

        data = {
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.post(url, data, **headers, format='json')

        self.assertEqual(resp.status_code, 400)
        hubspot.assert_not_called()

    @patch("utils.hubspot.send_cx_manager_message")
    def test_should_return_400_when_no_message_over_length(self, hubspot):
        sf_id = "321SOMEID123"
        url = '/api/1.0.0/message/'
        token = self.create_and_login_user('fakeloginuser')
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        hubspot.return_value = Response(status=200)

        customer = Customer.objects.create(email=user_email, name="Some Name")
        app = Application.objects.create(customer=customer, new_salesforce=sf_id)

        data = {
            "body":
            "Dl7dHz9Zuskgu2bNVKrr9s0PSUHe7Y67obZp8UkKwVuqnXw0EmyJckrDbgJ946XdtxAE4zaJIy77BTybQ7\
            bv8e21yXOX3omt5EyaJLdu4g0RmD60AIsrlrHNXQTs9HB9TXms4ONNhQOVB9lsF4xoDMOL24QKXppGNmguj\
            fotUCPttuW3k51T4z1IADhlJ3vgAl1PxPjEHYfWEr0KNLTHLxxVXruZysrfVwpEcYdPwDXltiQctXlXuoGg\
            gaZHtRP6X7d2CS0XayD2737SuRJnZ4avRMcyP48TRAFyAFaXbE2fb6gTbuL6r7TmFnUkiGgpwhClByDc7AO\
            wCPBhijnfTdycnxkkwUWXlJJQ6LpDsq5NKqrmzxvPJv3Fz496FmsRmjdsWSgj95AUJLUJVn75OGwAb8C2Dv\
            eg0wdcn3fkFy1mwTMdrZQ9BviDYuLEidYSmQrF6f78iO6kqM8d7zHAmez7IyWhNz4t6uViVEYsM2v160CGU\
            IIdIfedf9EChashg5OX6M6AU0UI56rqzMKiVzQ8Fno9boIgOPVBucodPXrSBUNHF3teIjdxeUikoxzxtTBu\
            osgVdDqWWwO12tYe8t5VIB0aVRs6DupHJTdN5JnSrDhPZWLW9D45vWdjfaHIzHkOEWxB6aWAOMvFEhNAGRF\
            vITeI4U6r2hIwh7OjYiuMkftloF8ZOIlMWy4eKUH6yPCX0l4mRcYsrs2979ww6DWl5bn3zgXLewsKAxYoVV\
            axfUgWVx1ECkobqFeqcx444WQk1VfuHAuzUmOrQJ8pfgurIlZtSZc6vHbNeqlzkUWr7AqRCuVNe5Qu1pVJn\
            t6SdDTz5y2sjZVh8EVzMOnYjIL7bJWC9GWfNbwMLOQ7yxfKqrp3vYghRGCdwpp5EDm0zI4pxl2Ib4UlLSBF\
            5qMRxV9WFHAkcIl0yG8ubRFochH3UyGNPpfOkcMD8kQmukngmiFwpDoaV3ViiMEmqJdllB4ZzZ9eg595NHb\
            LYnuJin7me2b9gq4PbuEgnhj1Hv097aqO1boDI9gvTWca57T1qBt5KcFy3u6h5Y2B7c6mCXcPgzlD2PUhki\
            6wlOrIoDIJuV8ul1JY5B8GJkWbRW3ZozZTlvaMKyOFgZ1AAOkjEVMPXzZlL4drUOZ7TaQDgg8WUTGvoQOls\
            J3pvSVr68x2fbz7HsZTR9RbsxnKOpd9FJY2GvIxKOokvII2ztDQt2ZnLMZffyLSQ7FXDwBKI7dwi9Aeai8q\
            MzlOpS7ZIF1UGG86okx9Qr3ckdWqzxvUL4P2oIHSRItI1m2cMF0tPAsr4lWonu04x2kfUVLxNp44vXb4rgB\
            KBZRL1zpE6pUAOH5ADSmemu5bwX9xUm47jb4inbxn9PVF06YcR9WAhOk79lbh71jFiiRs8GA9be0e51C5Sp\
            mRk8dyGbjaFzg1Vmkg29QmyZ8pPv9LFyf1aThDhntGBGdMosLtRLu5oYEANYymPCWZkHETOyhRQMiPfA1lW\
            Cu0lT0QU" # 1501 characters
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.post(url, data, **headers, format='json')

        self.assertEqual(resp.status_code, 400)
        hubspot.assert_not_called()

    @patch("utils.hubspot.send_cx_manager_message")
    def test_should_return_500_when_hubspot_fails(self, hubspot):
        sf_id = "321SOMEID123"
        url = '/api/1.0.0/message/'
        token = self.create_and_login_user('fakeloginuser')
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        hubspot.return_value = Response(status=400)

        customer = Customer.objects.create(email=user_email, name="Some Name")
        app = Application.objects.create(customer=customer, new_salesforce=sf_id)
        app.cx_manager = InternalSupportUser.objects.create(email="somecx@homeward.com")
        app.save()

        data = {
            "body": "asddfasdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf asdf",
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.post(url, data, **headers, format='json')

        self.assertEqual(resp.status_code, 500)
