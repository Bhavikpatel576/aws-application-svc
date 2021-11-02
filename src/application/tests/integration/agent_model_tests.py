from unittest.mock import patch

from application.models.real_estate_agent import RealEstateAgent
from rest_framework.test import APITestCase
from parameterized import parameterized


class RealEstateAgentModelTests(APITestCase):
    @parameterized.expand([
        ('happy path', "agenta", "agentb", True, True, "111-111-1111", "222-222-2222", "brandon+dsfmgklaetrjg@homeward.com", False),
        ('identical sf_ids', "same_id", "same_id", True, True, "111-111-1111", "222-222-2222", "brandon+dsfmgklaetrjg@homeward.com", True),
        ('identical sf_ids not certified', "same_id", "same_id", False, True, "111-111-1111", "222-222-2222", "brandon+dsfmgklaetrjg@homeward.com", True),
        ('identical phone nums', "agenta", "agentb", True, True, "111-111-1111", "111-111-1111", "brandon+dsfmgklaetrjg@homeward.com", True),
        ('identical phone nums not certified', "agenta", "agentb", True, False, "111-111-1111", "111-111-1111", "brandon+dsfmgklaetrjg@homeward.com", False),
        ('missing sf_id certified', None, "agentb", True, True, "111-111-1111", "222-222-2222", "brandon+dsfmgklaetrjg@homeward.com", True),
        ('missing phone certified', "agenta", "agentb", True, True, "111-111-1111", None, "brandon+dsfmgklaetrjg@homeward.com", True),
        ('empty phone certified', "agenta", "agentb", True, True, "111-111-1111", "", "brandon+dsfmgklaetrjg@homeward.com", True),
        ('empty sf_id certified', "agenta", "", True, True, "111-111-1111", "222-222-2222", "brandon+dsfmgklaetrjg@homeward.com", True),
        ('empty email certified', "agenta", "", True, True, "111-111-1111", "222-222-2222", "", True),
        ('missing email certified', "agenta", "", True, True, "111-111-1111", "222-222-2222", None, True),
    ])
    def test_real_estate_agent_inserts(self, name, sf_id_a, sf_id_b, is_certified_a, is_certified_b, phone_number_a,
                                       phone_number_b, email, should_not_save):
        agent_a = {
            "sf_id": sf_id_a,
            "name":"Brandon Kirchner",
            "phone":phone_number_a,
            "email":email,
            "company":"brandons brokerage",
            "is_certified":is_certified_a
        }

        agent_b = {
            "sf_id": sf_id_b,
            "name":"Robbie Bise",
            "phone":phone_number_b,
            "email":email,
            "company":"robbies brokerage",
            "is_certified":is_certified_b
        }

        if should_not_save:
            with self.assertRaises(Exception):
                RealEstateAgent.objects.create(**agent_a)
                RealEstateAgent.objects.create(**agent_b)

        else:
            RealEstateAgent.objects.create(**agent_a)
            RealEstateAgent.objects.create(**agent_b)

    @parameterized.expand([
        ('flat-phone', '1234567890', '1234567890', '(123) 456-7890'),
        ('sf format', '(123) 456-7890', '1234567890', '(123) 456-7890'),
        ('dash', '123-456-7890', '1234567890', '(123) 456-7890'),
        ('dot', '123.456.7890', '1234567890', '(123) 456-7890'),
        ('country', '+1(123) 456-7890', '1234567890', '(123) 456-7890'),
        ('non numeric string', 'asdf', '', Exception("Cannot format phone", '')),
        ('Number', 8675309, '8675309', Exception("Cannot format phone", 8675309)),
        ('empty', '', '', Exception("Cannot format phone", '')),
        ('None', None, None, Exception("Cannot format phone", None)),
    ])
    def test_real_estate_agent_flat_phone_formatting(self, name, phone_num, expected_phone_num, formatted_phone):
        agent_data = {
            "sf_id": "abcd",
            "name": "Robbie Bise",
            "phone": phone_num,
            "email": "robbie+dsfmgklaetrjg@homeward.com",
            "company": "robbies brokerage",
            "is_certified": False
        }
        if isinstance(formatted_phone, Exception):
            with self.assertRaises(Exception) as ex:
                RealEstateAgent.objects.create(**agent_data)
                self.assertEquals(ex, formatted_phone)
        else:
            saved_agent = RealEstateAgent.objects.create(**agent_data)
            self.assertEqual(formatted_phone, saved_agent.get_formatted_phone())
            self.assertEqual(expected_phone_num, saved_agent.phone)

