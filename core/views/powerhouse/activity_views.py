"""Powerhouse: Activity log list (view only)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import ActivityLog, UserRole
from core.serializers import ActivityLogSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_list(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    qs = ActivityLog.objects.all().select_related('user', 'game').order_by('-created_at')[:500]
    return Response(ActivityLogSerializer(qs, many=True).data)
