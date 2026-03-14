from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role, get_masters_queryset
from core.models import SuperSetting, User, UserRole
from core.serializers import SuperSettingSerializer


def _verify_pin(request):
    """Verify admin PIN from request.data. Returns None or error Response."""
    pin = request.data.get('pin')
    if not pin:
        return Response({'detail': 'PIN required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_master(request):
    err = require_role(request, [UserRole.POWERHOUSE, UserRole.SUPER])
    if err:
        return err
    pin_err = _verify_pin(request)
    if pin_err:
        return pin_err
    master_id = request.data.get('master_id')
    if master_id is None:
        return Response({'detail': 'master_id required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        master_id = int(master_id)
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid master_id.'}, status=status.HTTP_400_BAD_REQUEST)
    if request.user.role == UserRole.SUPER:
        allowed = get_masters_queryset(request.user).filter(pk=master_id).exists()
    else:
        allowed = User.objects.filter(pk=master_id, role=UserRole.MASTER).exists()
    if not allowed:
        return Response({'detail': 'Master not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)
    obj = SuperSetting.get_settings() or SuperSetting()
    obj.default_master_id = master_id
    obj.save()
    return Response({'default_master': master_id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def super_setting_get(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SuperSetting.get_settings()
    return Response(SuperSettingSerializer(obj).data if obj else None)


@api_view(['POST', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def super_setting_save(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SuperSetting.get_settings() or SuperSetting()
    ser = SuperSettingSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
