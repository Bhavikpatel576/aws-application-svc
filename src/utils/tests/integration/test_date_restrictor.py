import datetime

from django.test import TestCase

from application.models.application import ApplicationStage
from application.models.offer import OfferStatus
from application.tests import random_objects
from utils.date_restrictor import calculate_dates_at_capacity
from utils.date_restrictor import MAXIMUM_CLOSING_CAPACITY


class DateRestrictionTests(TestCase):

    def test_date_restrictor_returns_empty_list_if_no_dates_at_capacity(self):
        restricted_dates = calculate_dates_at_capacity(datetime.datetime.today(), datetime.datetime.today() + datetime.timedelta(weeks=52))
        self.assertEqual(len(restricted_dates), 0)

    def test_date_restrictor_returns_date_at_capacity(self):
        date_at_capacity = datetime.date.today() + datetime.timedelta(days=1)
        for _ in range(MAXIMUM_CLOSING_CAPACITY + 1):
            app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.WON)

        restricted_dates = calculate_dates_at_capacity(datetime.date.today(),
                                                       datetime.date.today() + datetime.timedelta(weeks=52))

        self.assertIn(date_at_capacity, restricted_dates)

    def test_date_restrictor_respects_start_date(self):
        date_at_capacity = datetime.date.today() + datetime.timedelta(days=1)
        for _ in range(MAXIMUM_CLOSING_CAPACITY):
            app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.WON)

        app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
        random_objects.random_offer(application=app,
                                    finance_approved_close_date=datetime.date.today() - datetime.timedelta(days=1),
                                    status=OfferStatus.WON)

        restricted_dates = calculate_dates_at_capacity(datetime.date.today(),
                                                       datetime.date.today() + datetime.timedelta(weeks=52))

        self.assertEqual(len(restricted_dates), 0)

    def test_date_restrictor_respects_end_date(self):
        date_at_capacity = datetime.date.today() + datetime.timedelta(days=1)
        for _ in range(MAXIMUM_CLOSING_CAPACITY):
            app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.WON)

        app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
        random_objects.random_offer(application=app,
                                    finance_approved_close_date=datetime.datetime.today() + datetime.timedelta(weeks=53),
                                    status=OfferStatus.WON)

        restricted_dates = calculate_dates_at_capacity(datetime.datetime.today(),
                                                       datetime.datetime.today() + datetime.timedelta(weeks=52))

        self.assertEqual(len(restricted_dates), 0)

    def test_date_restrictor_respects_weighting_correctly(self):
        date_at_capacity = datetime.date.today() + datetime.timedelta(days=1)
        for _ in range(MAXIMUM_CLOSING_CAPACITY - 1):
            app = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.WON)

        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                    status=OfferStatus.REQUESTED)

        restricted_dates = calculate_dates_at_capacity(datetime.datetime.today(),
                                                       datetime.datetime.today() + datetime.timedelta(weeks=52))

        self.assertEqual(len(restricted_dates), 0)

        for _ in range(2):
            app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.REQUESTED)

        restricted_dates = calculate_dates_at_capacity(datetime.datetime.today(),
                                                       datetime.datetime.today() + datetime.timedelta(weeks=52))

        self.assertEqual(len(restricted_dates), 1)

    def test_date_restrictor_respects_application_stage_correctly(self):
        date_at_capacity = datetime.datetime.now() + datetime.timedelta(days=1)
        for _ in range(MAXIMUM_CLOSING_CAPACITY + 1):
            app = random_objects.random_application(stage=ApplicationStage.CANCELLED_CONTRACT)
            random_objects.random_offer(application=app, finance_approved_close_date=date_at_capacity,
                                        status=OfferStatus.WON)

        restricted_dates = calculate_dates_at_capacity(datetime.datetime.today(), datetime.datetime.today() + datetime.timedelta(weeks=52))

        self.assertEqual(len(restricted_dates), 0)
