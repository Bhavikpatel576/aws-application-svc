"""
User app views.
"""
from cas.views import _logout_url
from django.contrib.auth import logout
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import (HTTP_400_BAD_REQUEST, HTTP_200_OK)
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from user.models import UserCustomView

from .. import serializers


class CASView(APIView):

    permission_classes = (AllowAny, )

    @staticmethod
    def post(request):
        serializer = serializers.CASSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid(raise_exception=True):
            new_data = serializer.validated_data
            token = AuthToken.objects.create(new_data['user'])
            return Response({'token': token[1]}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class MEView(APIView):
    """
    User view to get User details.
    """

    def get(self, request):
        return Response(serializers.UserSerializerWithGroups(request.user).data)


class LogoutView(APIView):
    """
    User logout View.
    """

    authentication_classes = (TokenAuthentication,)

    def delete(self, request):
        try:
            logout(request)
        except Exception as e:
            print("Logging logout action error: %s" % e)
        return Response(data={'redirect_to': _logout_url(request)}, status=HTTP_200_OK)


class UserCustomViewViewSet(ModelViewSet):
    """
    ModelViewSet for UserCustomView.
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = serializers.UserCustomViewSerializer

    def get_queryset(self):
        """
        Get custom views of logged in user.
        """
        return UserCustomView.objects.filter(user=self.request.user).order_by('name')

    def perform_create(self, serializer):
        """
        Custom perform create method.
        """
        serializer.validated_data.update({
            'user': self.request.user
        })
        serializer.save()

    def perform_update(self, serializer):
        """
        Custom perform update method.
        """
        serializer.validated_data.update({
            'user': self.request.user
        })
        serializer.save()
