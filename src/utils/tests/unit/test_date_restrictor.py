import datetime

from django.test import SimpleTestCase

from application.models.application import ProductOffering
from utils.date_restrictor import calculate_dates_at_capacity
from utils.date_restrictor import get_latest_close_date, get_weekend_dates, get_holidays
from utils.date_restrictor import get_earliest_close_date


class DateRestrictionTests(SimpleTestCase):
    def test_returns_date_bwc(self):
        fake_created_at = datetime.datetime(2021, 8, 9)
        expected_date_bwc = datetime.date(2021, 8, 26)
        assert expected_date_bwc == get_earliest_close_date(ProductOffering.BUY_ONLY, fake_created_at)

    def test_return_date_bbys(self):
        fake_created_at = datetime.datetime(2021, 8, 9)
        expected_date_bbys = datetime.date(2021, 8, 30)
        assert expected_date_bbys == get_earliest_close_date(ProductOffering.BUY_SELL, fake_created_at)
    
    def test_date_restrictor_get_date_18_months_in_future(self):
        date_input = datetime.datetime(2021, 8, 19)
        expected_date_in_18_months = datetime.date(2023, 2, 19)
        actual_date_in_18_months = get_latest_close_date(date_input)
        self.assertEqual(expected_date_in_18_months, actual_date_in_18_months, "Future date was not correct.")

    def test_weekend_date_calculator(self):
        start_date = datetime.date(2021, 9, 4)
        end_date = datetime.date(2021, 9, 18)

        dates = get_weekend_dates(start_date, end_date)

        self.assertEqual(len(dates), 5)
        self.assertIn(datetime.date(2021, 9, 4), dates)
        self.assertIn(datetime.date(2021, 9, 5), dates)
        self.assertIn(datetime.date(2021, 9, 11), dates)
        self.assertIn(datetime.date(2021, 9, 12), dates)
        self.assertIn(datetime.date(2021, 9, 18), dates)

    def test_holiday_date_calculator(self):
        start_date = datetime.date(2020, 1, 1)
        end_date = datetime.date(2021, 1, 1)

        dates = get_holidays(start_date, end_date)

        self.assertEqual(len(dates), 11)
        self.assertIn(datetime.date(2020, 1, 1), dates)
        self.assertIn(datetime.date(2020, 4, 12), dates)
        self.assertIn(datetime.date(2020, 5, 25), dates)
        self.assertIn(datetime.date(2020, 7, 4), dates)
        self.assertIn(datetime.date(2020, 9, 7), dates)
        self.assertIn(datetime.date(2020, 11, 26), dates)
        self.assertIn(datetime.date(2020, 11, 27), dates)
        self.assertIn(datetime.date(2020, 12, 24), dates)
        self.assertIn(datetime.date(2020, 12, 25), dates)
        self.assertIn(datetime.date(2020, 12, 31), dates)
        self.assertIn(datetime.date(2021, 1, 1), dates)
