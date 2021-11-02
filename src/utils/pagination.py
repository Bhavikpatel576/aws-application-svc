"""
Overriden pagination classes.
"""

from rest_framework.pagination import PageNumberPagination as BasePageNumberPagination


class PageNumberPagination(BasePageNumberPagination):
    """
    Custom pagination class.
    """

    page_size_query_param = 'page_size'
