from rest_framework import viewsets, generics
from api.v1_0_0.permissions import IsApplicationBuyingAgent
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.v1_0_0.serializers.blend_serializers import FollowupSerializer
from blend.models import Followup


class CustomerFollowupView(generics.ListAPIView):
    serializer_class = FollowupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Followup.objects.filter(application__customer__email=self.request.user.email)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class AgentFollowupView(generics.ListAPIView):
    serializer_class = FollowupSerializer
    permission_classes = [IsAuthenticated, IsApplicationBuyingAgent]

    def get_queryset(self):
        return Followup.objects.filter(application__buying_agent__email__iexact=self.request.user.email)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)
