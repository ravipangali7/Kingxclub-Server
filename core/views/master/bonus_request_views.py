from decimal import Decimal, InvalidOperation
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from core.permissions import require_role
from core.models import BonusRequest, UserRole
from core.serializers import BonusRequestSerializer
from core.services.bonus_request_service import approve_bonus_request


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bonus_request_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = BonusRequest.objects.filter(user__parent=request.user).select_related('user', 'bonus_rule', 'processed_by').order_by('-created_at')
    search = request.query_params.get('search', '').strip()
    if search:
        qs = qs.filter(user__username__icontains=search)
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        qs = qs.filter(status=status_filter)
    date_from = request.query_params.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    date_to = request.query_params.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return Response(BonusRequestSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def bonus_request_detail(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    obj = BonusRequest.objects.filter(pk=pk, user__parent=request.user).select_related('user', 'bonus_rule', 'processed_by').first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'PATCH':
        if obj.status != 'pending':
            return Response({'detail': 'Only pending bonus requests can be edited.'}, status=status.HTTP_400_BAD_REQUEST)
        amount_raw = request.data.get('amount')
        if amount_raw is None:
            return Response({'detail': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(amount_raw))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'detail': 'Amount must be positive.'}, status=status.HTTP_400_BAD_REQUEST)
        obj.amount = amount
        obj.save(update_fields=['amount'])
        return Response(BonusRequestSerializer(obj, context={'request': request}).data)
    return Response(BonusRequestSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bonus_request_approve(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    br = BonusRequest.objects.filter(pk=pk, user__parent=request.user, status='pending').first()
    if not br:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    ok, msg = approve_bonus_request(br, request.user)
    if not ok:
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(BonusRequestSerializer(br, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bonus_request_reject(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    br = BonusRequest.objects.filter(pk=pk, user__parent=request.user, status='pending').first()
    if not br:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    br.status = 'rejected'
    br.reject_reason = request.data.get('reject_reason', '')
    br.processed_by = request.user
    br.processed_at = timezone.now()
    br.save()
    return Response(BonusRequestSerializer(br, context={'request': request}).data)
