from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import User, UserRole
from core.serializers import UserMinimalSerializer, KycListSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kyc_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = User.objects.filter(role=UserRole.PLAYER, kyc_status='pending', parent=request.user)
    return Response(KycListSerializer(qs, many=True, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kyc_approve(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    user = User.objects.filter(pk=pk, role=UserRole.PLAYER, parent=request.user).first()
    if not user:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    user.kyc_status = 'approved'
    user.kyc_approved_by = request.user
    user.kyc_reject_reason = ''
    user.save(update_fields=['kyc_status', 'kyc_approved_by', 'kyc_reject_reason'])
    return Response(UserMinimalSerializer(user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kyc_reject(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    user = User.objects.filter(pk=pk, role=UserRole.PLAYER, parent=request.user).first()
    if not user:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    user.kyc_status = 'rejected'
    user.kyc_reject_reason = request.data.get('reason', '')
    user.save(update_fields=['kyc_status', 'kyc_reject_reason'])
    return Response(UserMinimalSerializer(user).data)
