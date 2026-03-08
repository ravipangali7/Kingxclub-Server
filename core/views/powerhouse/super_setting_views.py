from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import SuperSetting, UserRole
from core.serializers import SuperSettingSerializer


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
