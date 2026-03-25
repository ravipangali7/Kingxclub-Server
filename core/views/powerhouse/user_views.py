"""Powerhouse: Super, Master, Player CRUD."""
import secrets
from django.db.models import Q, Sum, Subquery, OuterRef, Max
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role, get_supers_queryset, get_masters_queryset, get_players_queryset
from core.models import User, UserRole, Deposit, Withdraw, GameLog, Transaction, ActivityLog
from core.serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateUpdateSerializer,
    DepositSerializer, WithdrawSerializer, GameLogSerializer,
    TransactionSerializer, ActivityLogSerializer,
)


def _get_queryset(request, role_type):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err, None
    if role_type == 'super':
        qs = get_supers_queryset(request.user)
    elif role_type == 'master':
        qs = get_masters_queryset(request.user)
    else:
        qs = get_players_queryset(request.user)
    return None, qs


def _user_list_response(request, role_type):
    """Shared list logic; request is DRF Request. Returns Response."""
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    search = request.query_params.get('search', '').strip()
    if search:
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
    if role_type == 'player':
        master_id = request.query_params.get('master_id', '').strip()
        if master_id:
            try:
                qs = qs.filter(parent_id=int(master_id))
            except (ValueError, TypeError):
                pass
        gl_max = GameLog.objects.filter(user_id=OuterRef('pk')).values('user_id').annotate(m=Max('created_at')).values('m')[:1]
        dep_max = Deposit.objects.filter(user_id=OuterRef('pk')).values('user_id').annotate(m=Max('created_at')).values('m')[:1]
        wd_max = Withdraw.objects.filter(user_id=OuterRef('pk')).values('user_id').annotate(m=Max('created_at')).values('m')[:1]
        qs = qs.annotate(
            _win_sum=Sum('game_logs__win_amount'),
            _lose_sum=Sum('game_logs__lose_amount'),
            _bet_sum=Sum('game_logs__bet_amount'),
            _last_gl=Subquery(gl_max),
            _last_dep=Subquery(dep_max),
            _last_wd=Subquery(wd_max),
        )
    serializer = UserListSerializer(qs.order_by('-created_at'), many=True)
    return Response(serializer.data)


def _user_detail_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(UserDetailSerializer(obj).data)


def _user_create_response(request, role_type):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    role_map = {'super': UserRole.SUPER, 'master': UserRole.MASTER, 'player': UserRole.PLAYER}
    data = request.data.copy()
    if role_type == 'master':
        data.pop('whatsapp_deposit', None)
        data.pop('whatsapp_withdraw', None)
    data['role'] = role_map[role_type]
    if role_type == 'super':
        data['parent'] = request.user.id
    elif role_type == 'master':
        data['parent'] = data.get('parent')
    elif role_type == 'player':
        data['parent'] = data.get('parent')
    ser = UserCreateUpdateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


def _user_update_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
    if role_type == 'master':
        data.pop('whatsapp_deposit', None)
        data.pop('whatsapp_withdraw', None)
    ser = UserCreateUpdateSerializer(obj, data=data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(UserDetailSerializer(obj).data)


def _user_delete_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _verify_admin_pin(request):
    """Verify admin PIN from request.data. Returns None or error Response."""
    pin = request.data.get('pin')
    if not pin:
        return Response({'detail': 'PIN required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    return None


def _user_regenerate_pin_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    pin_err = _verify_admin_pin(request)
    if pin_err:
        return pin_err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    new_pin = ''.join(secrets.choice('0123456789') for _ in range(6))
    obj.pin = new_pin
    obj.save(update_fields=['pin'])
    return Response({'detail': 'PIN regenerated successfully.'})


def _user_reset_password_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    pin_err = _verify_admin_pin(request)
    if pin_err:
        return pin_err
    new_password = request.data.get('new_password')
    if not new_password:
        return Response({'detail': 'new_password required.'}, status=status.HTTP_400_BAD_REQUEST)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.set_password(new_password)
    obj.save(update_fields=['password'])
    return Response({'detail': 'Password reset successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request, role_type):
    return _user_list_response(request, role_type)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, role_type, pk):
    return _user_detail_response(request, role_type, pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create(request, role_type):
    return _user_create_response(request, role_type)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update(request, role_type, pk):
    return _user_update_response(request, role_type, pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request, role_type, pk):
    return _user_delete_response(request, role_type, pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_supers(request):
    return _user_list_response(request, 'super')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_masters(request):
    return _user_list_response(request, 'master')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_players(request):
    return _user_list_response(request, 'player')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_supers(request, pk):
    return _user_detail_response(request, 'super', pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_masters(request, pk):
    return _user_detail_response(request, 'master', pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_players(request, pk):
    return _user_detail_response(request, 'player', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_super(request):
    return _user_create_response(request, 'super')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_master(request):
    return _user_create_response(request, 'master')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_player(request):
    return _user_create_response(request, 'player')


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_super(request, pk):
    return _user_update_response(request, 'super', pk)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_master(request, pk):
    return _user_update_response(request, 'master', pk)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_player(request, pk):
    return _user_update_response(request, 'player', pk)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def user_toggle_active_player(request, pk):
    """Requires PIN; sets player is_active to request.data['is_active'] (bool)."""
    err, qs = _get_queryset(request, 'player')
    if err:
        return err
    pin_err = _verify_admin_pin(request)
    if pin_err:
        return pin_err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    is_active = request.data.get('is_active')
    if is_active is None:
        return Response({'detail': 'is_active required.'}, status=status.HTTP_400_BAD_REQUEST)
    obj.is_active = bool(is_active)
    obj.save(update_fields=['is_active'])
    return Response(UserDetailSerializer(obj).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_super(request, pk):
    return _user_delete_response(request, 'super', pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_master(request, pk):
    return _user_delete_response(request, 'master', pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_player(request, pk):
    return _user_delete_response(request, 'player', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_regenerate_pin_super(request, pk):
    return _user_regenerate_pin_response(request, 'super', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_regenerate_pin_master(request, pk):
    return _user_regenerate_pin_response(request, 'master', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_regenerate_pin_player(request, pk):
    return _user_regenerate_pin_response(request, 'player', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password_super(request, pk):
    return _user_reset_password_response(request, 'super', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password_master(request, pk):
    return _user_reset_password_response(request, 'master', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password_player(request, pk):
    return _user_reset_password_response(request, 'player', pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_report(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    qs = get_players_queryset(request.user)
    player = qs.filter(pk=pk).first()
    # Powerhouse: if not in players queryset (e.g. user is not role=Player), still allow viewing by pk
    if not player and request.user.role == UserRole.POWERHOUSE:
        player = User.objects.filter(pk=pk).first()
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
