"""Powerhouse: read-only list of Coming Soon Enrollments."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import ComingSoonEnrollment, UserRole
from core.serializers import ComingSoonEnrollmentSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def coming_soon_enrollment_list(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    qs = ComingSoonEnrollment.objects.select_related('game', 'user').order_by('-created_at')
    serializer = ComingSoonEnrollmentSerializer(qs, many=True)
    return Response(serializer.data)
