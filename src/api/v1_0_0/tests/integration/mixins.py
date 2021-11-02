"""
API Test v1 mixins
"""
from knox.models import AuthToken

from application.models.address import Address
from application.models.application import Application
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.models import CurrentHomeImage
from user.models import (User, UserCustomView)

from api.v1_0_0.tests._utils.data_generators import (get_fake_user, get_fake_address, get_fake_customer, get_fake_application,
                              get_fake_currenthome, get_fake_current_home_image)


class AuthMixin:
    """
    Auth mixin.
    """

    def create_user(self, key):
        user_data = get_fake_user(key)
        return User.objects.create_user(**user_data)

    def create_admin(self, key):
        user_data = get_fake_user(key)
        return User.objects.create_user(**user_data, is_staff=True)

    def login_user(self, user):
        return AuthToken.objects.create(user)

    def create_and_login_user(self, key):
        user = self.create_user(key)
        token = self.login_user(user)
        return token[1]

    def create_and_login_admin(self, key):
        admin = self.create_admin(key)
        token = self.login_user(admin)
        return token[1]

    def create_customer(self, key):
        customer_data = get_fake_customer(key)
        return Customer.objects.create(**customer_data)

    def create_address(self, key):
        address_data = get_fake_address(key)
        return Address.objects.create(**address_data)

    def create_currenthome(self, key):
        currenthome_data = get_fake_currenthome(key)
        currenthome_data['address'] = self.create_address(key)
        return CurrentHome.objects.create(**currenthome_data)

    def create_application(self, key):
        application_data = get_fake_application(key)
        application_data['customer'] = self.create_customer(key)
        application_data['current_home'] = self.create_currenthome(key)
        return Application.objects.create(**application_data)

    def create_current_home_image(self, key, current_home=None):
        current_home_image_data = get_fake_current_home_image(key, current_home)
        return CurrentHomeImage.objects.create(**current_home_image_data)

    def create_user_custom_view(self, name, user):
        return UserCustomView.objects.create(name=name, user=user, application_listing_fields=[])
