from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0_0.serializers.acknowledgement_serializer import AcknowledgementSerializer
from application.models.acknowledgement import Acknowledgement
from application.models.application import Application
from application.task_operations import run_task_operations


class AcknowledgementViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'patch']
    serializer_class = AcknowledgementSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Acknowledgement.objects.filter(application__customer__email=self.request.user.email, disclosure__active=True).all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data={**request.data, 'ip_address': request.stream.META.get('REMOTE_ADDR')},
                                         partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        application = Application.objects.get(customer__email=self.request.user.email)
        run_task_operations(application)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
