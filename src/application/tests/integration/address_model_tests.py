from rest_framework.test import APITestCase

from application.models.address import Address

class AddressModelTests(APITestCase):
    def setUp(self) -> None:
        self.address = Address.objects.create(**{
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            })
    
    def test_get_inline_address(self): 
        self.assertEqual(self.address.get_inline_address(), '123 Main Street, Austin, TX, 78701')
    
    def test_get_street_and_zip_address(self): 
        self.assertEqual(self.address.street_and_zip_address(), '123 Main Street 78701')
    
    def test_will_not_throw_error_if_zip_missing(self):
        missing_zip_address = Address.objects.create(**{
            "street": "12324 Main Street",
            "city": "Austin",
            "state": "TX"
        })
        self.assertEqual(missing_zip_address.street_and_zip_address(), '12324 Main Street.')