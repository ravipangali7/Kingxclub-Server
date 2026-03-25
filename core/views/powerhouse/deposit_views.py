"""Powerhouse: Deposit list, detail, create, approve/reject."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from core.permissions import require_role
from core.models import Deposit, User, UserRole, PaymentMode
from core.serializers import DepositSerializer, DepositCreateSerializer, PaymentModeSerializer
from core.services.reference_id_validation import validate_ref_unique


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_payment_modes(request):
    """Return payment modes for deposit target (user_id). For player target returns parent's modes."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'detail': 'user_id required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid user_id.'}, status=status.HTTP_400_BAD_REQUEST)
    target = User.objects.filter(
        pk=user_id,
        role__in=[UserRole.SUPER, UserRole.MASTER, UserRole.PLAYER]
    ).first()
    if not target:
        return Response({'detail': 'User not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)
    owner_id = target.parent_id if target.role == UserRole.PLAYER else user_id
    qs = PaymentMode.objects.filter(user_id=owner_id, status='approved')
    return Response(PaymentModeSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_list(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    qs = Deposit.objects.all().select_related('user', 'payment_mode', 'processed_by').order_by('-created_at')
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
    serializer = DepositSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def deposit_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = Deposit.objects.filter(pk=pk).select_related('user', 'payment_mode').first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'PATCH':
        update_fields = []
        if 'amount' in request.data and obj.status == 'pending':
            from decimal import Decimal
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
                    ref = '' if val is None else str(val).strip()
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
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    ser = DepositCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user_id = request.data.get('user_id')
    from core.models import Deposit as DepositModel
    dep = DepositModel.objects.create(user_id=user_id, **ser.validated_data)
    return Response(DepositSerializer(dep, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_direct(request):
    """
    Verify PIN first; only then create and approve deposit. No deposit is created if PIN is invalid.
    Body: pin, user_id, amount, remarks (optional).
    """
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    pin = request.data.get('pin')
    password = request.data.get('password')
    if pin is not None and pin != '':
        if not request.user.pin or request.user.pin != pin:
            return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    elif password is not None and password != '':
        if not request.user.check_password(password):
            return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'detail': 'PIN or password required.'}, status=status.HTTP_400_BAD_REQUEST)

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
        from decimal import Decimal
        amount = Decimal(str(amount_raw))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    from core.models import User
    target_user = User.objects.filter(
        pk=user_id,
        role__in=[UserRole.SUPER, UserRole.MASTER, UserRole.PLAYER]
    ).first()
    if not target_user:
        return Response({'detail': 'User not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)

    from core.models import Deposit as DepositModel, PaymentMode
    from core.services.deposit_service import approve_deposit

    owner_id = target_user.parent_id if target_user.role == UserRole.PLAYER else user_id
    payment_mode_id = request.data.get('payment_mode')
    payment_mode = None
    if payment_mode_id is not None:
        payment_mode = PaymentMode.objects.filter(pk=payment_mode_id, user_id=owner_id).first()
        if not payment_mode:
            return Response({'detail': 'Invalid payment mode.'}, status=status.HTTP_400_BAD_REQUEST)

    dep = DepositModel.objects.create(
        user_id=user_id,
        amount=amount,
        remarks=remarks,
        reference_id=reference_id,
        status='pending',
        payment_mode_id=payment_mode.pk if payment_mode else None,
    )
    ok, msg = approve_deposit(dep, request.user)
    if not ok:
        dep.delete()
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DepositSerializer(dep, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_approve(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    pin = request.data.get('pin')
    password = request.data.get('password')
    if pin is not None and pin != '':
        if not request.user.pin or request.user.pin != pin:
            return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    elif password is not None and password != '':
        if not request.user.check_password(password):
            return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'detail': 'PIN or password required.'}, status=status.HTTP_400_BAD_REQUEST)
    dep = Deposit.objects.filter(pk=pk, status='pending').first()
    if not dep:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    from core.services.deposit_service import approve_deposit
    ok, msg = approve_deposit(dep, request.user)
    if not ok:
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DepositSerializer(dep, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_reject(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    dep = Deposit.objects.filter(pk=pk, status='pending').first()
    if not dep:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    dep.status = 'rejected'
    dep.reject_reason = request.data.get('reject_reason', '')
    dep.processed_by = request.user
    dep.processed_at = timezone.now()
    dep.save()
    return Response(DepositSerializer(dep, context={'request': request}).data)
