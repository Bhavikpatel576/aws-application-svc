"""
Views for market value analysis in application.
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser

from application.models.models import (MarketValuation, MarketValueOpinionComment, Comparable)
from .. import serializers


class MarketValuationViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin,
                             viewsets.GenericViewSet):
    """
    Viewset for market value analysis.
    """

    serializer_class = serializers.MarketValuationSerializer
    permission_classes = (IsAdminUser,)
    lookup_field = 'current_home'

    def get_queryset(self):
        """
        Custom function to get market value analysis queryset.
        """
        return MarketValuation.objects.all()


class MarketValueOpinionCommentViewSet(viewsets.ModelViewSet):
    """
    Viewset to delete Market value Opinion Comment.
    """

    queryset = MarketValueOpinionComment.objects.all()
    serializer_class = serializers.MarketValueOpinionCommentSerializer
    http_method_names = 'delete'
    permission_classes = (IsAdminUser,)


class ComparableViewSet(viewsets.ModelViewSet):
    """
    Viewset to delete Comparable.
    """

    queryset = Comparable.objects.all()
    serializer_class = serializers.ComparableSerializer
    http_method_names = 'delete'
    permission_classes = (IsAdminUser,)
