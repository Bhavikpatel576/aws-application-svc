"""
User app serializers.
"""
from django.conf import settings
from django.contrib import auth
from django.db.models import Q

from rest_framework import serializers

from cas.views import proxy_callback

from user.models import User, UserCustomView


class CASSerializer(serializers.Serializer):      # pylint: disable=abstract-method
    ticket = serializers.CharField()
    service = serializers.CharField()

    def validate(self, data):

        auth_data = {'ticket': data['ticket'], 'service': data['service']}
        user = auth.authenticate(**auth_data)
        if not user:
            raise serializers.ValidationError(
                "Authentication failed from CAS server"
            )
        auth.login(self.context['request'], user)
        if settings.CAS_PROXY_CALLBACK:
            proxy_callback(self.context['request'])
        data.update({'user': user})
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'username', 'last_name')


class UserSerializerWithGroups(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'username', 'last_name', 'groups')

    def get_groups(self, obj):
        return obj.fetch_cas_groups()


class UserCustomViewSerializer(serializers.ModelSerializer):
    """
    Model serializer for model UserCustomView.
    """

    def validate_name(self, name):
        """
        validate condition : one user can not create a custom view with same name.
        """
        if UserCustomView.objects.filter(user=self.context['request'].user, name__iexact=name).exclude(id=getattr(getattr(self, 'instance', object), 'pk', None)).exists():
            raise serializers.ValidationError('This custom view already exists.')
        return name

    def update(self, instance, validated_data):
        """
        Custom update method.
        """
        if validated_data.get('is_default', False):
            UserCustomView.objects.filter(Q(user=self.context['request'].user) & ~Q(pk=instance.pk)).update(is_default=False)
        return super(UserCustomViewSerializer, self).update(instance, validated_data)

    class Meta:
        model = UserCustomView
        fields = "__all__"
        read_only_fields = ('id', 'user')
