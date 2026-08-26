from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Allows only operational ADMIN users.

    SuperAdmin is intentionally NOT handled here.
    """

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        return (
            getattr(user, "role", None) == "ADMIN"
            and not user.is_superuser
            and getattr(user, "is_active", True)
        )