from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import UserRole, ActivityAction
from core.serializers import UserDetailSerializer
from core.services.activity_log_service import create_activity_log

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_get(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    return Response(UserDetailSerializer(request.user).data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_update(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    u = request.user
    for f in ['name', 'phone', 'email', 'whatsapp_number']:
        if f in request.data: setattr(u, f, request.data[f])
    u.save()
    create_activity_log(request.user, ActivityAction.PROFILE_UPDATE, request=request)
    return Response(UserDetailSerializer(u).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    new = request.data.get('new_password')
    if not new: return Response({'detail': 'New password is required.'}, status=400)
    if len(new) < 6: return Response({'detail': 'Password must be at least 6 characters.'}, status=400)
    request.user.set_password(new)
    request.user.save()
    create_activity_log(request.user, ActivityAction.PASSWORD_CHANGE, request=request)
    return Response({'detail': 'OK'})
