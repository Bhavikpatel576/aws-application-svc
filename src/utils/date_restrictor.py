import datetime
from typing import List

import pytz
from dateutil.easter import easter
from dateutil.relativedelta import relativedelta, MO, TH
from django.db.models import Case, When, Value, Sum, Q, FloatField

from application.models.application import ApplicationStage
from application.models.application import ProductOffering
from application.models.offer import Offer, OfferStatus

RESTRICTED_DATE_RANGES = {ProductOffering.BUY_ONLY: datetime.timedelta(days=17),
                          ProductOffering.BUY_SELL: datetime.timedelta(days=21)}

MAXIMUM_CLOSING_CAPACITY = 15
MAXIMUM_TIME_TO_CLOSE_IN_MONTHS = 18


def get_earliest_close_date(product_offering, offer_created_at: datetime.datetime, date_ranges=None) -> datetime.date:
    """returns earliest possible date for closing on a given product

    Args:
        product_offering (ProductOffering): the specific product
        offer_created_at (datetime.datetime): the day from which to calculate
        date_ranges (dict): if not passed, defaults to constant in module

    Returns:
        Str: ISO formatted date.
    """
    date_ranges = date_ranges or RESTRICTED_DATE_RANGES
    return offer_created_at.date() + date_ranges[product_offering]


def calculate_restricted_dates(start_date: datetime.date, end_date: datetime.date) -> List[datetime.date]:
    """
    Holistically determines which dates are restricted between start and end dates (inclusive)
    :param start_date: the earliest date in the date range you want to check
    :param end_date: the latest date in the date range you want to check
    :return:  list of dates that are restricted.
    """

    return calculate_dates_at_capacity(start_date, end_date) + get_weekend_dates(start_date, end_date) + \
           get_holidays(start_date, end_date)


def calculate_dates_at_capacity(start_date: datetime.date, end_date: datetime.date) -> List[datetime.date]:
    """
    Determines which dates, if any, are restricted due to already being at capacity,
    based on number of scheduled closings.

        Args:
            start_date (date): the earliest date in the date range you want to check
            end_date (date): the latest date in the date range you want to check

        Returns:
            List[date]: a list of dates that are at capacity (empty list if there are none).
        """
    return list(Offer.objects \
                .filter(finance_approved_close_date__gt=start_date, finance_approved_close_date__lt=end_date) \
                .annotate(capacity_weight=Case(
        When(Q(application__stage__in=[ApplicationStage.QUALIFIED_APPLICATION, ApplicationStage.FLOOR_PRICE_REQUESTED,
                                       ApplicationStage.FLOOR_PRICE_COMPLETED, ApplicationStage.APPROVED,
                                       ApplicationStage.OFFER_REQUESTED, ApplicationStage.OFFER_SUBMITTED],
               status__in=[OfferStatus.REQUESTED, OfferStatus.MOP_COMPLETE, OfferStatus.APPROVED,
                           OfferStatus.BACKUP_POSITION_ACCEPTED]),
             then=Value(0.45)),
        (When(Q(application__stage__in=[ApplicationStage.OPTION_PERIOD, ApplicationStage.POST_OPTION],
                status=OfferStatus.WON),
              then=Value(1.0))
         ), default=Value(0.0), output_field=FloatField()))
                .values('finance_approved_close_date')
                .annotate(weighted_num_offers=Sum('capacity_weight'))
                .filter(weighted_num_offers__gt=MAXIMUM_CLOSING_CAPACITY)
                .values_list('finance_approved_close_date', flat=True))


def get_latest_close_date(offer_created_date: datetime.datetime) -> datetime.date:
    return offer_created_date.date() + relativedelta(months=MAXIMUM_TIME_TO_CLOSE_IN_MONTHS)
    

def current_homeward_date():
    return datetime.datetime.now().date()


def date_range(start_date: datetime.date, end_date: datetime.date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)


def get_weekend_dates(start_date: datetime.date, end_date: datetime.date) -> List[datetime.date]:
    """
    Returns a list of all Saturdays and Sundays between start_date and end_date (inclusive)
    :param start_date: the first date to check for saturday / sunday-ness
    :param end_date: the last date to check for saturday / sunday-ness
    :return: a list of dates that are all saturday or sunday.
    """
    # weekdays are represented numerically, with Monday being 0 and sunday being 6
    weekend_day_indexes = [5, 6]
    weekend_days = []
    for date in date_range(start_date, end_date):
        if date.weekday() in weekend_day_indexes:
            weekend_days.append(date)

    return weekend_days


def get_holidays(start_date: datetime.date, end_date: datetime.date) -> List[datetime.date]:
    """
    Returns a list of holidays in between the two given dates.
    :param start_date: the beginning of the date range
    :param end_date: the end of the date range
    :return: a list of holidays that fall within the date range
    """
    years = range(start_date.year, end_date.year + 1)
    non_variable_holiday_dates = [
        # month, day tuples
        (1, 1),  # New Years Day
        (7, 4),  # Independence Day
        (12, 24),  # Christmas Eve
        (12, 25),  # Christmas Day
        (12, 31),  # New Years Eve
    ]
    holidays = []

    for year in years:
        potential_holidays = []
        for holiday in non_variable_holiday_dates:
            potential_holidays.append(datetime.date(year, holiday[0], holiday[1]))

        good_friday = easter(year)
        memorial_day = datetime.date(year, 5, 1) + relativedelta(day=31, weekday=MO(-1))
        labor_day = datetime.date(year, 9, 1) + relativedelta(weekday=MO)
        thanksgiving = datetime.date(year, 11, 1) + relativedelta(weekday=TH(+4))
        day_after_thanksgiving = thanksgiving + datetime.timedelta(days=1)

        potential_holidays += [good_friday, memorial_day, labor_day, thanksgiving, day_after_thanksgiving]

        for holiday_date in potential_holidays:
            if start_date <= holiday_date <= end_date:
                holidays.append(holiday_date)

    return holidays
