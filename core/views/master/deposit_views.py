from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from core.permissions import require_role, get_players_queryset
from core.models import Deposit, PaymentMode, UserRole
from core.serializers import DepositSerializer, DepositCreateSerializer
from core.services.deposit_service import approve_deposit
from core.services.reference_id_validation import validate_ref_unique

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = Deposit.objects.filter(user__parent=request.user).select_related('user', 'payment_mode').order_by('-created_at')
    search = request.query_params.get('search', '').strip()
    if search:
        qs = qs.filter(Q(user__username__icontains=search) | Q(reference_id__icontains=search))
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        qs = qs.filter(status=status_filter)
    date_from = request.query_params.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    date_to = request.query_params.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return Response(DepositSerializer(qs, many=True, context={'request': request}).data)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def deposit_detail(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    obj = Deposit.objects.filter(pk=pk, user__parent=request.user).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'PATCH':
        update_fields = []
        if 'amount' in request.data and obj.status == 'pending':
            try:
                new_amount = Decimal(str(request.data['amount']))
            except (TypeError, ValueError):
                return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
            if new_amount <= 0:
                return Response({'detail': 'Amount must be positive.'}, status=status.HTTP_400_BAD_REQUEST)
            obj.amount = new_amount
            update_fields.append('amount')
        for key in ('remarks', 'reference_id'):
            if key in request.data:
                val = request.data.get(key)
                if key == 'reference_id':
                    ref = (val if val is not None else '').strip() if isinstance(val, str) else (str(val).strip() if val is not None else '')
                    ok, err_msg = validate_ref_unique(ref, exclude_deposit_id=obj.pk)
                    if not ok:
                        return Response({'detail': err_msg}, status=status.HTTP_400_BAD_REQUEST)
                    setattr(obj, key, ref)
                else:
                    setattr(obj, key, val if val is not None else '')
                update_fields.append(key)
        if update_fields:
            obj.save(update_fields=update_fields)
        return Response(DepositSerializer(obj, context={'request': request}).data)
    return Response(DepositSerializer(obj, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_create(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    ser = DepositCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    dep = Deposit.objects.create(user_id=request.data.get('user_id'), **ser.validated_data)
    return Response(DepositSerializer(dep, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_direct(request):
    """Verify PIN first; only then create and approve deposit. No deposit created if PIN is invalid."""
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.data.get('user_id')
    amount_raw = request.data.get('amount')
    remarks = request.data.get('remarks', '') or ''
    reference_id = (request.data.get('reference_id') or '').strip()
    if reference_id:
        ok, err_msg = validate_ref_unique(reference_id)
        if not ok:
            return Response({'detail': err_msg}, status=status.HTTP_400_BAD_REQUEST)
    if user_id is None:
        return Response({'detail': 'user_id required.'}, status=status.HTTP_400_BAD_REQUEST)
    if amount_raw is None:
        return Response({'detail': 'amount required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount_raw))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    if not get_players_queryset(request.user).filter(pk=user_id).exists():
        return Response({'detail': 'User not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)

    payment_mode_id = request.data.get('payment_mode')
    payment_mode = None
    if payment_mode_id is not None:
        payment_mode = PaymentMode.objects.filter(pk=payment_mode_id, user=request.user).first()
        if not payment_mode:
            return Response({'detail': 'Invalid payment mode.'}, status=status.HTTP_400_BAD_REQUEST)

    dep = Deposit.objects.create(
        user_id=user_id, amount=amount, remarks=remarks, reference_id=reference_id, status='pending',
        payment_mode_id=payment_mode.pk if payment_mode else None
    )
    ok, msg = approve_deposit(dep, request.user)
    if not ok:
        dep.delete()
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DepositSerializer(dep, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_approve(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    dep = Deposit.objects.filter(pk=pk, user__parent=request.user, status='pending').first()
    if not dep:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    ok, msg = approve_deposit(dep, request.user)
    if not ok:
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DepositSerializer(dep, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_reject(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    dep = Deposit.objects.filter(pk=pk, user__parent=request.user, status='pending').first()
    if not dep:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    dep.status = 'rejected'
    dep.reject_reason = request.data.get('reject_reason', '')
    dep.processed_by = request.user
    dep.processed_at = timezone.now()
    dep.save()
    return Response(DepositSerializer(dep, context={'request': request}).data)
