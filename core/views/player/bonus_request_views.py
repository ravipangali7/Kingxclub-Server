from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import BonusRequest, BonusType, UserRole
from core.serializers import BonusRequestSerializer, BonusRequestCreateSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bonus_request_create(request):
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    bonus_type = (request.data.get('bonus_type') or '').strip().lower()
    if bonus_type not in [c[0] for c in BonusType.choices]:
        return Response(
            {'detail': 'Invalid bonus_type. Must be one of: welcome, deposit, referral.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    ser = BonusRequestCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data.copy()
    data['bonus_type'] = bonus_type
    br = BonusRequest.objects.create(user=request.user, **data)
    return Response(BonusRequestSerializer(br, context={'request': request}).data, status=status.HTTP_201_CREATED)
