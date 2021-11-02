from rest_framework import permissions

from application.models.models import Note


class NotePermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.user.is_staff:
            if view.action in ['update', 'partial_update', 'destroy']:
                return bool(Note.objects.filter(author=request.user, pk=view.kwargs.get('pk')).exists())
            return True
        return False
