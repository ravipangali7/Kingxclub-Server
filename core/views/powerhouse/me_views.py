from decimal import Decimal, InvalidOperation

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import User, UserRole, ActivityAction
from core.serializers import UserDetailSerializer
from core.services.activity_log_service import create_activity_log


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_get(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    return Response(UserDetailSerializer(request.user).data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_update(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    u = request.user
    for f in ['name', 'phone', 'email', 'whatsapp_number']:
        if f in request.data:
            setattr(u, f, request.data[f])
    if 'main_balance' in request.data:
        try:
            val = Decimal(str(request.data['main_balance']))
            if val < 0:
                return Response({'detail': 'main_balance must be >= 0.'}, status=400)
            User.objects.filter(pk=u.pk).update(main_balance=val)
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Invalid main_balance.'}, status=400)
    u.save(update_fields=['name', 'phone', 'email', 'whatsapp_number'])
    if 'main_balance' in request.data:
        u.refresh_from_db()
    create_activity_log(request.user, ActivityAction.PROFILE_UPDATE, request=request)
    return Response(UserDetailSerializer(u).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    old = request.data.get('old_password')
    new = request.data.get('new_password')
    if not old or not new:
        return Response({'detail': 'Required.'}, status=400)
    if not request.user.check_password(old):
        return Response({'detail': 'Invalid password.'}, status=400)
    request.user.set_password(new)
    request.user.save()
    create_activity_log(request.user, ActivityAction.PASSWORD_CHANGE, request=request)
    return Response({'detail': 'OK'})
