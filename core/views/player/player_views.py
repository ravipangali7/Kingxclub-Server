from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import User, UserRole, Deposit, Withdraw, BonusRequest, Transaction, GameLog, PaymentMode
from core.serializers import DepositSerializer, WithdrawSerializer, BonusRequestSerializer, TransactionSerializer, GameLogSerializer, PaymentModeSerializer, ReferralSerializer, BonusRuleSerializer
from core.services.deposit_service import get_applicable_deposit_bonus_rule
from core.services.withdraw_eligibility import get_withdraw_eligibility


def _get_related_transaction(game_log):
    """Return the transaction linked to this game log (by FK or by user + remarks)."""
    if hasattr(game_log, 'transactions') and game_log.transactions.exists():
        return game_log.transactions.first()
    return Transaction.objects.filter(
        user=game_log.user,
        remarks=f"Game round {game_log.round}",
    ).first()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    u = request.user
    ctx = {'request': request}
    eligibility = get_withdraw_eligibility(u)
    return Response({
        'main_balance': str(u.main_balance or 0),
        'bonus_balance': str(u.bonus_balance or 0),
        'main_withdrawable': str(eligibility['main_withdrawable']),
        'bonus_withdrawable': str(eligibility['bonus_withdrawable']),
        'total_withdrawable': str(eligibility['total_withdrawable']),
        'can_withdraw_main': eligibility['can_withdraw_main'],
        'can_withdraw_bonus': eligibility['can_withdraw_bonus'],
        'deposits': DepositSerializer(Deposit.objects.filter(user=u).select_related('payment_mode', 'payment_mode__payment_method').order_by('-created_at')[:50], many=True, context=ctx).data,
        'withdrawals': WithdrawSerializer(Withdraw.objects.filter(user=u).select_related('payment_mode', 'payment_mode__payment_method').order_by('-created_at')[:50], many=True, context=ctx).data,
        'bonus_requests': BonusRequestSerializer(BonusRequest.objects.filter(user=u).select_related('bonus_rule').order_by('-created_at')[:50], many=True, context=ctx).data,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    return Response(TransactionSerializer(Transaction.objects.filter(user=request.user).order_by('-created_at')[:200], many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_list(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    return Response(GameLogSerializer(GameLog.objects.filter(user=request.user).select_related('game', 'game__category', 'provider').order_by('-created_at')[:200], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_detail(request, pk):
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    log = GameLog.objects.filter(user=request.user, pk=pk).select_related('game', 'game__category', 'provider', 'user').first()
    if not log:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    tx = _get_related_transaction(log)
    return Response({
        'game_log': GameLogSerializer(log).data,
        'transaction': TransactionSerializer(tx).data if tx else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_list(request):
    """Return users referred by the current player (referred_by=request.user)."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    qs = User.objects.filter(referred_by=request.user).order_by('-created_at')
    return Response(ReferralSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_detail(request, pk):
    """Return one referred user only if they were referred by the current player."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    user = User.objects.filter(pk=pk, referred_by=request.user).first()
    if not user:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(ReferralSerializer(user).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_bonus_eligibility(request):
    """Return whether current user is eligible for first-deposit bonus and the applicable rule (for modal preview)."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    is_first_deposit = Deposit.objects.filter(user=request.user, status='approved').count() == 0
    rule = get_applicable_deposit_bonus_rule()
    applicable_rule = BonusRuleSerializer(rule).data if rule else None
    return Response({
        'is_first_deposit': is_first_deposit,
        'applicable_rule': applicable_rule,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_payment_modes(request):
    """Return master's (parent's) payment modes for deposit. Player selects one when requesting deposit."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    parent = request.user.parent
    if not parent:
        return Response([])
    qs = PaymentMode.objects.filter(user=parent, status='approved').select_related('payment_method')
    return Response(PaymentModeSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payment_mode_list_create(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    if request.method == 'GET':
        return Response(PaymentModeSerializer(PaymentMode.objects.filter(user=request.user).select_related('payment_method'), many=True, context={'request': request}).data)
    data = request.data.copy()
    if request.FILES:
        for key in request.FILES:
            data[key] = request.FILES[key]
    data['user'] = request.user.id
    ser = PaymentModeSerializer(data=data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(PaymentModeSerializer(ser.instance, context={'request': request}).data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def payment_mode_detail(request, pk):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    obj = PaymentMode.objects.filter(pk=pk, user=request.user).first()
    if not obj: return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET': return Response(PaymentModeSerializer(obj, context={'request': request}).data)
    if request.method == 'DELETE': obj.delete(); return Response(status=status.HTTP_204_NO_CONTENT)
    ser = PaymentModeSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(PaymentModeSerializer(ser.instance, context={'request': request}).data)
