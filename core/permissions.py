"""
Role-based permission helpers for function-based views.
"""
from rest_framework.response import Response
from rest_framework import status
from .models import User, UserRole


def require_role(request, allowed_roles):
    """
    If request.user is not authenticated or role not in allowed_roles, return a 403 Response.
    Otherwise return None (caller proceeds).
    """
    if not request.user or not request.user.is_authenticated:
        return Response(
            {'detail': 'Authentication credentials were not provided.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if request.user.role not in allowed_roles:
        return Response(
            {'detail': 'You do not have permission to perform this action.'},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


def get_users_queryset_for_role(user):
    """
    Return User queryset that the given user is allowed to see/manage.
    - powerhouse: all users (filter by role for supers, masters, players)
    - super: all masters (children) and all players under those masters
    - master: only direct children (players)
    """
    from django.db.models import Q
    if user.role == UserRole.POWERHOUSE:
        return User.objects.all()
    if user.role == UserRole.SUPER:
        # Masters that are direct children + players under those masters
        return User.objects.filter(
            Q(parent=user, role=UserRole.MASTER) |
            Q(parent__parent=user, role=UserRole.PLAYER)
        )
    if user.role == UserRole.MASTER:
        return User.objects.filter(parent=user, role=UserRole.PLAYER)
    return User.objects.none()


def get_supers_queryset(user):
    """Powerhouse only: all users with role SUPER (Powerhouse sees all supers)."""
    if user.role != UserRole.POWERHOUSE:
        return User.objects.none()
    return User.objects.filter(role=UserRole.SUPER)


def get_masters_queryset(user):
    """Super: direct children masters. Powerhouse: all masters."""
    if user.role == UserRole.POWERHOUSE:
        return User.objects.filter(role=UserRole.MASTER)
    if user.role == UserRole.SUPER:
        return User.objects.filter(parent=user, role=UserRole.MASTER)
    return User.objects.none()


def get_players_queryset(user):
    """Master: direct children players. Super: players under their masters. Powerhouse: all players."""
    if user.role == UserRole.POWERHOUSE:
        return User.objects.filter(role=UserRole.PLAYER)
    if user.role == UserRole.SUPER:
        return User.objects.filter(parent__parent=user, role=UserRole.PLAYER)
    if user.role == UserRole.MASTER:
        return User.objects.filter(parent=user, role=UserRole.PLAYER)
    return User.objects.none()
