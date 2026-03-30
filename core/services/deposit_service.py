"""
Deposit approval: parent main_balance deducted, user main_balance added.
Dual transactions. Powerhouse: only adjust super balance (no parent deduction).
First-deposit bonus: if player's first approved deposit and an applicable deposit
bonus rule exists, credit bonus to user's bonus_balance and create BONUS transaction.
"""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q

from core.models import (
    User,
    UserRole,
    Deposit,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
    BonusRule,
    BonusRequest,
    BonusType,
    RewardType,
)
from core.notification_utils import notify_player_approval


def _deposit_reference_id(deposit):
    return (getattr(deposit, 'reference_id', '') or '').strip()


def get_applicable_deposit_bonus_rule():
    """
    Return the single applicable deposit bonus rule (active, current time within
    valid_from/valid_until). Same rule used for eligibility preview and for
    crediting on first approved deposit. None means no limit for that bound.
    """
    now = timezone.now()
    return (
        BonusRule.objects.filter(
            bonus_type=BonusType.DEPOSIT,
            is_active=True,
        )
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=now))
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
        .order_by('id')
        .first()
    )


def approve_deposit(deposit, processed_by, pin=None, use_password=False):
    """
    Approve a deposit. For powerhouse->super: only add to super. For others: deduct parent, add to user.
    Returns (True, None) or (False, error_message).
    """
    user = deposit.user
    amount = deposit.amount
    if user.role == UserRole.SUPER and processed_by.role == UserRole.POWERHOUSE:
        user.main_balance = (user.main_balance or Decimal('0')) + amount
        user.save(update_fields=['main_balance'])
        deposit.status = 'approved'
        deposit.processed_by = processed_by
        deposit.processed_at = timezone.now()
        deposit.save(update_fields=['status', 'processed_by', 'processed_at'])
        ref = _deposit_reference_id(deposit)
        Transaction.objects.create(
            user=user,
            action_type=TransactionActionType.IN,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            remarks=f'Deposit #{deposit.pk} approved',
            processed_by=processed_by,
            reference_id=ref,
        )
        if user.role == UserRole.PLAYER:
            notify_player_approval(user, processed_by, f'Your deposit of ₹{amount} has been approved.')
        return True, None
    parent = user.parent
    if not parent:
        return False, 'User has no parent'
    if (parent.main_balance or Decimal('0')) < amount:
        return False, 'Parent has insufficient balance'
    parent.main_balance = (parent.main_balance or Decimal('0')) - amount
    parent.save(update_fields=['main_balance'])
    user.main_balance = (user.main_balance or Decimal('0')) + amount
    user.save(update_fields=['main_balance'])
    deposit.status = 'approved'
    deposit.processed_by = processed_by
    deposit.processed_at = timezone.now()
    deposit.save(update_fields=['status', 'processed_by', 'processed_at'])
    ref = _deposit_reference_id(deposit)
    Transaction.objects.create(
        user=parent,
        action_type=TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.DEPOSIT,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        to_user=user,
        remarks=f'Deposit #{deposit.pk} for {user.username}',
        processed_by=processed_by,
        reference_id=ref,
    )
    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.DEPOSIT,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=parent,
        remarks=f'Deposit #{deposit.pk} approved',
        processed_by=processed_by,
        reference_id=ref,
    )
    if user.role == UserRole.PLAYER:
        notify_player_approval(user, processed_by, f'Your deposit of ₹{amount} has been approved.')
        # First-deposit bonus: staff-initiated deposits skip; player-requested first approval still gets bonus
        if not deposit.suppress_first_deposit_bonus:
            approved_count = Deposit.objects.filter(user=user, status='approved').count()
            if approved_count == 1:
                rule = get_applicable_deposit_bonus_rule()
                if rule:
                    if rule.reward_type == RewardType.FLAT:
                        bonus_amount = rule.reward_amount
                    else:
                        bonus_amount = (deposit.amount * rule.reward_amount / 100).quantize(Decimal('0.01'))
                    if bonus_amount > 0:
                        BonusRequest.objects.create(
                            user=user,
                            amount=bonus_amount,
                            bonus_type=BonusType.DEPOSIT,
                            bonus_rule=rule,
                            status='approved',
                            processed_by=processed_by,
                            processed_at=timezone.now(),
                            remarks=f'First deposit bonus (Deposit #{deposit.pk})',
                        )
                        user.bonus_balance = (user.bonus_balance or Decimal('0')) + bonus_amount
                        user.save(update_fields=['bonus_balance'])
                        parent.main_balance = (parent.main_balance or Decimal('0')) - bonus_amount
                        parent.save(update_fields=['main_balance'])
                        Transaction.objects.create(
                            user=parent,
                            action_type=TransactionActionType.OUT,
                            wallet=TransactionWallet.MAIN_BALANCE,
                            transaction_type=TransactionType.BONUS,
                            amount=bonus_amount,
                            status=TransactionStatus.SUCCESS,
                            to_user=user,
                            remarks=f'First deposit bonus for {user.username}',
                            processed_by=processed_by,
                            reference_id=ref,
                        )
                        Transaction.objects.create(
                            user=user,
                            action_type=TransactionActionType.IN,
                            wallet=TransactionWallet.BONUS_BALANCE,
                            transaction_type=TransactionType.BONUS,
                            amount=bonus_amount,
                            status=TransactionStatus.SUCCESS,
                            remarks=f'First deposit bonus (Deposit #{deposit.pk})',
                            processed_by=processed_by,
                            reference_id=ref,
                        )
    return True, None
