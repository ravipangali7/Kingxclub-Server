from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import User, UserRole
from core.serializers import UserDetailSerializer
from core.services.settlement_service import settle_master


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def settle(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    master = User.objects.filter(pk=pk, role=UserRole.MASTER, parent=request.user).first()
    if not master:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    ok, msg = settle_master(master, request.user)
    if not ok:
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(UserDetailSerializer(master).data)
