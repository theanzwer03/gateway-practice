from rest_framework.permissions import BasePermission

from .models import User


def is_gateway_admin(principal):
    return (
        isinstance(principal, User)
        and principal.is_authenticated
        and principal.is_active
        and principal.role == User.Role.ADMIN
    )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_gateway_admin(request.user)
