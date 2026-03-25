"""Read-only reject reason suggestions from SuperSetting (master, super, powerhouse)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import SuperSetting, UserRole
from core.permissions import require_role


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reject_reason_suggestions(request):
    err = require_role(request, [UserRole.MASTER, UserRole.SUPER, UserRole.POWERHOUSE])
    if err:
        return err
    settings = SuperSetting.get_settings()
    data = []
    if settings is not None:
        raw = getattr(settings, 'reject_reason_suggestions', None) or {}
        if isinstance(raw, dict):
            inner = raw.get('data')
            if isinstance(inner, list):
                data = [str(x) for x in inner if x is not None and str(x).strip() != '']
    return Response({'data': data})
