"""
Application app filters.
"""
import django_filters
from django.db.models import Q


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class ApplicationFilterSet(django_filters.FilterSet):
    """
    Application model filterset.
    """
    id = django_filters.CharFilter(field_name='id', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name='customer__name', lookup_expr='icontains')
    stage = CharInFilter(field_name='stage', lookup_expr='in')
    start_date = django_filters.CharFilter(method='filter_start_date')
    email = django_filters.CharFilter(field_name='customer__email', lookup_expr='icontains')
    phone = django_filters.CharFilter(field_name='customer__phone', lookup_expr='icontains')
    home_buying_stage = CharInFilter(field_name='home_buying_stage', lookup_expr='in')
    agents_name = django_filters.CharFilter(field_name='real_estate_agent__name', lookup_expr='icontains')
    agents_phone = django_filters.CharFilter(field_name='real_estate_agent__phone', lookup_expr='icontains')
    agents_email = django_filters.CharFilter(field_name='real_estate_agent__email', lookup_expr='icontains')
    builder__company_name = django_filters.CharFilter(field_name='builder__company_name', lookup_expr='icontains')
    shopping_location = django_filters.CharFilter(field_name='shopping_location', lookup_expr='icontains')
    lender_name = django_filters.CharFilter(field_name='mortgage_lender__name', lookup_expr='icontains')
    lender_email = django_filters.CharFilter(field_name='mortgage_lender__email', lookup_expr='icontains')
    lender_phone = django_filters.CharFilter(field_name='mortgage_lender__phone', lookup_expr='icontains')
    max_price = django_filters.CharFilter(field_name='max_price', lookup_expr='icontains')
    min_price = django_filters.CharFilter(field_name='min_price', lookup_expr='icontains')
    move_in = CharInFilter(field_name='move_in', lookup_expr='in')
    move_by_date = django_filters.CharFilter(field_name='move_by_date', lookup_expr='icontains')
    builder__address = django_filters.CharFilter(method='filter_address')
    offer_property_address = django_filters.CharFilter(method='filter_address')
    address = django_filters.CharFilter(method='filter_address')
    lead_source = django_filters.CharFilter(field_name='lead_source', lookup_expr="icontains")
    lead_source_drill_down_1 = django_filters.CharFilter(field_name="lead_source_drill_down_1", lookup_expr="icontains")
    agent_service_buying_agent_id = django_filters.CharFilter(field_name='agent_service_buying_agent_id', lookup_expr='icontains')

    def filter_start_date(self, queryset, name, value):
        """
        Filter start date.
        """

        if '{' in value:
            value = eval(value)  # pylint: disable=eval-used
            return queryset.filter(start_date__range=(value['from_date'], value['to_date']))
        return queryset.filter(start_date__date=value)

    def filter_address(self, queryset, address_type, value_string):
        """
        Filter by address.
        """
        if address_type == 'address':
            address_type = 'current_home__address'
        if address_type and value_string:
            return queryset.filter(
                Q(**{('{}__street__icontains'.format(address_type)): value_string.strip()})
                or Q(**{('{}__city__icontains'.format(address_type)): value_string.strip()})
                or Q(**{('{}__state__icontains'.format(address_type)): value_string.strip()})
                or Q(**{('{}__zip__icontains'.format(address_type)): value_string.strip()})
            )
        return queryset
