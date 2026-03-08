"""Super: List masters' payment modes (pending), approve/reject."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from core.permissions import require_role, get_masters_queryset
from core.models import PaymentMode, UserRole
from core.serializers import PaymentModeSerializer


def _qs(request):
    """Payment modes belonging to super's masters."""
    masters = get_masters_queryset(request.user)
    return PaymentMode.objects.filter(user__in=masters)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_mode_verification_list(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    status_filter = request.query_params.get('status')
    qs = _qs(request).select_related('user', 'action_by', 'payment_method').order_by('-created_at')
    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)
    return Response(PaymentModeSerializer(qs, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_mode_approve(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    obj = _qs(request).filter(pk=pk, status='pending').first()
    if not obj:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    obj.status = 'approved'
    obj.reject_reason = ''
    obj.action_by = request.user
    obj.action_at = timezone.now()
    obj.save()
    return Response(PaymentModeSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_mode_reject(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    obj = _qs(request).filter(pk=pk, status='pending').first()
    if not obj:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    obj.status = 'rejected'
    obj.reject_reason = request.data.get('reject_reason', '')
    obj.action_by = request.user
    obj.action_at = timezone.now()
    obj.save()
    return Response(PaymentModeSerializer(obj, context={'request': request}).data)
