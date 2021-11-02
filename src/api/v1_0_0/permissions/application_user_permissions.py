from application.models.application import Application
from django.shortcuts import get_object_or_404
from rest_framework import permissions


class IsApplicationUser(permissions.BasePermission):
    def has_permission(self, request, view):
        user_email = request.user.email
        application_id = request.resolver_match.kwargs.get('application_id')
        app = get_object_or_404(Application, pk=application_id)
        if app.customer.email == user_email:
            return True
        return False
