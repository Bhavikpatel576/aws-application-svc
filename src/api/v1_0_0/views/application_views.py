"""
Application app views.
"""
import logging
from api.v1_0_0.permissions.application_user_permissions import IsApplicationUser
from application.task_operations import update_photo_task, update_current_home_task

from django.db.models import Prefetch
from rest_framework import mixins, status, viewsets

from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from api.v1_0_0 import filters, permissions, serializers
from application.models.models import (Application, CurrentHomeImage,
                                       CurrentHomeImageStatus, Note)
from application.models.real_estate_agent import AgentType, RealEstateAgent
from application.task_operations import run_task_operations
from application.tasks import (push_agent_to_salesforce, push_to_salesforce,
                               update_app_status, push_current_home_to_salesforce)
from utils.salesforce import (sync_loan_record_from_salesforce,
                              sync_record_from_salesforce)

logger = logging.getLogger(__name__)


class ApplicationCurrentHomeImageViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    http_method_names = ['post']
    serializer_class = serializers.CurrentHomeImageSerializer
    permission_classes = [IsAuthenticated, IsApplicationUser]

    def get_application(self):
        application_id = self.kwargs.get('application_id')
        return get_object_or_404(Application, id=application_id)

    def create(self, request, *args, **kwargs):
        app = self.get_application()
        resp = super().create(request, *args, **kwargs)
        update_photo_task(app)
        return resp

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ApplicationCurrentHomeViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    http_method_names = ['post', 'patch']
    serializer_class = serializers.ApplicationCurrentHomeSerializer
    permission_classes = [IsAuthenticated, IsApplicationUser]

    def get_application(self):
        application_id = self.kwargs.get('application_id')
        return get_object_or_404(Application, id=application_id)

    def get_object(self):
        app = self.get_application()
        if not app.current_home:
            raise Http404('No current home on application')
        return app.current_home

    def update(self, request, *args, **kwargs):
        app = self.get_application()
        resp = super().update(request, *args, **kwargs)
        update_current_home_task(app)
        push_current_home_to_salesforce.apply_async(kwargs={
            'application_id': app.id
        })
        return resp

    def perform_create(self, serializer):
        current_home = serializer.save()
        app = self.get_application()
        app.current_home = current_home
        app.save()
        update_current_home_task(app)
        push_current_home_to_salesforce.apply_async(kwargs={
            'application_id': app.id
        })


    def create(self, request, *args, **kwargs):
        app = self.get_application()
        if app.current_home:
            return Response(f"Application: {app.id} already has a current home", status=status.HTTP_409_CONFLICT)
        return super().create(request, *args, **kwargs)


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    Application model read only (list, retrieve) viewset.
    """

    http_method_names = ['get', 'post', 'patch', 'put']
    serializer_class = serializers.ApplicationSerializer
    permission_classes = (IsAdminUser, IsAuthenticated)
    ordering_fields = ('id', 'customer__name', 'stage', 'start_date',
                       'customer__email', 'customer__phone', 'home_buying_stage',
                       'current_home__address__street', 'current_home__address__city',
                       'current_home__address__state', 'current_home__address__zip',
                       'builder__address__street', 'builder__address__city',
                       'builder__address__state', 'builder__address__zip',
                       'real_estate_agent__name', 'real_estate_agent__email',
                       'real_estate_agent__phone', 'builder__company_name',
                       'shopping_location', 'mortgage_lender__name',
                       'mortgage_lender__email', 'mortgage_lender__phone',
                       'max_price', 'min_price', 'move_in', 'move_by_date',
                       'buying_agent_id', 'listing_agent_id',
                       )
    filter_class = filters.ApplicationFilterSet

    def get_queryset(self):
        """
        Custom get_queryset method.
        """
        current_home_images = CurrentHomeImage.objects.filter(status=CurrentHomeImageStatus.LABELED)
        return Application.objects.select_related('current_home', 'real_estate_agent', 'customer', 'mortgage_lender',
                                                  'builder', 'offer_property_address') \
            .prefetch_related(Prefetch('current_home__images', current_home_images)).order_by('-start_date')

    @action(methods=['get'], detail=False, url_path='task-status', permission_classes=[IsAuthenticated])
    def get_task_status(self, request):
        application = Application.objects.filter(customer__email=request.user.email).first()
        if application:
            status_history = application.task_statuses.all().order_by('task_obj__order')
            serializer = serializers.TaskStatusSerializer(status_history, many=True)
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, url_path='salesforce/loan', permission_classes=[IsAdminUser])
    def sync_loan_from_salesforce(self, request):
        payload = request.data
        logger.info("Syncing loan from salesforce", extra=dict(
            type="sync_loan_from_salesforce",
            payload=payload
        ))
        if isinstance(payload, list):
            for record in payload:
                if isinstance(record, dict):
                     sync_loan_record_from_salesforce.delay(record)
                else:
                    logger.warning('payload is not a list of dicts', extra=dict(type='payload_not_list_of_dicts'))
        elif isinstance(payload, dict):
            sync_loan_record_from_salesforce.delay(payload)
        else:
            logger.warning('payload is not a list OR dict', extra=dict(type='payload_not_list_or_dict'))

        return Response(status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='salesforce', permission_classes=[IsAdminUser])
    def sync_from_salesforce(self, request):
        salesforce_data = request.data
        sync_record_from_salesforce.delay(salesforce_data)

        return Response(status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='salesforce/bulk', permission_classes=[IsAdminUser])
    def bulk_salesforce(self, request):
        saleforce_records = request.data
        for record in saleforce_records:
            sync_record_from_salesforce.delay(record)

        return Response(status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='agents', permission_classes=[IsAuthenticated])
    def agents(self, request):
        serializer = serializers.AgentsSerializer(data=request.data)
        application = Application.objects.get(customer__email=request.user.email)

        if serializer.is_valid():
            agents_data = serializer.save()
            if agents_data.buying_agent:  # if agent exists on payload
                if agents_data.needs_buying_agent:  # and if needs agent
                    return Response(data='Cannot set buying_agent when need_buying_agent is True',
                                    status=status.HTTP_400_BAD_REQUEST)  # don't set, bad request
                buying_agent = RealEstateAgent.objects.create(**agents_data.buying_agent)  # otherwise set
                application.buying_agent = buying_agent  # add to application if all succeeds
                push_agent_to_salesforce(application, buying_agent, AgentType.BUYING)
            application.needs_buying_agent = agents_data.needs_buying_agent

            if agents_data.listing_agent:
                if agents_data.needs_listing_agent:
                    return Response(data='Cannot set listing_agent when need_listing_agent is True',
                                    status=status.HTTP_400_BAD_REQUEST)
                listing_agent = RealEstateAgent.objects.create(**agents_data.listing_agent)
                application.listing_agent = listing_agent
                push_agent_to_salesforce(application, listing_agent, AgentType.LISTING)
            application.needs_listing_agent = agents_data.needs_listing_agent

            application.save()
            run_task_operations(application)
        else:
            return Response(data='Invalid request data', status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        """
        Custom update method.
        """
        serializer.save()

        push_to_salesforce.apply_async(kwargs={
            'application_id': serializer.instance.pk
        })
        update_app_status.apply_async(kwargs={
            'application_id': serializer.instance.pk
        })


class NoteViewSet(viewsets.ModelViewSet):
    """
    Note's list, create, update and delete action viewset
    """
    queryset = Note.objects.all()
    serializer_class = serializers.NoteSerializer
    permission_classes = (permissions.NotePermissions,)
    pagination_class = None
    filterset_fields = ('application',)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
