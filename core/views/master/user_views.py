from django.db.models import Sum, Subquery, OuterRef, Max
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role, get_players_queryset
from core.models import UserRole, Deposit, Withdraw, GameLog, Transaction, ActivityLog
from core.serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateUpdateSerializer,
    DepositSerializer, WithdrawSerializer, GameLogSerializer,
    TransactionSerializer, ActivityLogSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    gl_max = GameLog.objects.filter(user_id=OuterRef('pk')).values('user_id').annotate(m=Max('created_at')).values('m')[:1]
    dep_max = Deposit.objects.filter(user_id=OuterRef('pk')).values('user_id').annotate(m=Max('created_at')).values('m')[:1]
    wd_max = Withdraw.objects.filter(user_id=OuterRef('pk')).values('user_id').annotate(m=Max('created_at')).values('m')[:1]
    qs = get_players_queryset(request.user).annotate(
        _win_sum=Sum('game_logs__win_amount'),
        _lose_sum=Sum('game_logs__lose_amount'),
        _bet_sum=Sum('game_logs__bet_amount'),
        _last_gl=Subquery(gl_max),
        _last_dep=Subquery(dep_max),
        _last_wd=Subquery(wd_max),
    ).order_by('-created_at')
    search = request.query_params.get('search', '').strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(username__icontains=search) | Q(name__icontains=search) | Q(phone__icontains=search))
    date_from = request.query_params.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    date_to = request.query_params.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    is_active = request.query_params.get('is_active', '')
    if is_active.lower() == 'true':
        qs = qs.filter(is_active=True)
    elif is_active.lower() == 'false':
        qs = qs.filter(is_active=False)
    return Response(UserListSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_detail(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(UserDetailSerializer(obj).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def player_create(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    data = request.data.copy()
    data['role'] = UserRole.PLAYER
    data['parent'] = request.user.id
    ser = UserCreateUpdateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


def _verify_master_pin(request):
    """Verify master PIN from request.data. Returns None or error Response."""
    pin = request.data.get('pin')
    if not pin:
        return Response({'detail': 'PIN required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    return None


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def player_update(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    pin_err = _verify_master_pin(request)
    if pin_err:
        return pin_err
    data = request.data.copy()
    data.pop('pin', None)
    data.pop('parent', None)
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    ser = UserCreateUpdateSerializer(obj, data=data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(UserDetailSerializer(obj).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def player_reset_password(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    pin_err = _verify_master_pin(request)
    if pin_err:
        return pin_err
    new_password = request.data.get('new_password')
    if not new_password:
        return Response({'detail': 'new_password required.'}, status=status.HTTP_400_BAD_REQUEST)
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.set_password(new_password)
    obj.save(update_fields=['password'])
    return Response({'detail': 'Password reset successfully.'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def player_delete(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def player_toggle_active(request, pk):
    """Requires PIN; sets player is_active to request.data['is_active'] (bool)."""
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    is_active = request.data.get('is_active')
    if is_active is None:
        return Response({'detail': 'is_active required.'}, status=status.HTTP_400_BAD_REQUEST)
    obj.is_active = bool(is_active)
    obj.save(update_fields=['is_active'])
    return Response(UserDetailSerializer(obj).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_report(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    player = qs.filter(pk=pk).first()
    if not player:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    date_from = request.query_params.get('date_from', '').strip()
    date_to = request.query_params.get('date_to', '').strip()

    total_balance = (player.main_balance or 0) + (player.bonus_balance or 0) + (player.exposure_balance or 0)
    gl_qs = GameLog.objects.filter(user=player)
    if date_from:
        gl_qs = gl_qs.filter(created_at__date__gte=date_from)
    if date_to:
        gl_qs = gl_qs.filter(created_at__date__lte=date_to)
    agg = gl_qs.aggregate(w=Sum('win_amount'), l=Sum('lose_amount'))
    total_win_loss = (agg['w'] or 0) - (agg['l'] or 0)

    dep_qs = Deposit.objects.filter(user=player).select_related('user', 'payment_mode').order_by('-created_at')
    wd_qs = Withdraw.objects.filter(user=player).select_related('user', 'payment_mode').order_by('-created_at')
    tx_qs = Transaction.objects.filter(user=player).select_related('user').order_by('-created_at')
    act_qs = ActivityLog.objects.filter(user=player).select_related('user', 'game').order_by('-created_at')
    if date_from:
        dep_qs = dep_qs.filter(created_at__date__gte=date_from)
        wd_qs = wd_qs.filter(created_at__date__gte=date_from)
        tx_qs = tx_qs.filter(created_at__date__gte=date_from)
        act_qs = act_qs.filter(created_at__date__gte=date_from)
    if date_to:
        dep_qs = dep_qs.filter(created_at__date__lte=date_to)
        wd_qs = wd_qs.filter(created_at__date__lte=date_to)
        tx_qs = tx_qs.filter(created_at__date__lte=date_to)
        act_qs = act_qs.filter(created_at__date__lte=date_to)

    context = {'request': request}
    return Response({
        'user': UserDetailSerializer(player).data,
        'total_balance': str(total_balance),
        'total_win_loss': str(total_win_loss),
        'deposits': DepositSerializer(dep_qs[:200], many=True, context=context).data,
        'withdrawals': WithdrawSerializer(wd_qs[:200], many=True, context=context).data,
        'game_logs': GameLogSerializer(gl_qs[:200], many=True).data,
        'transactions': TransactionSerializer(tx_qs[:200], many=True).data,
        'activity_logs': ActivityLogSerializer(act_qs[:200], many=True).data,
    })
