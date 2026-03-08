"""
Bonus request approval: parent main_balance deducted, user bonus_balance added.
Dual transactions. Powerhouse approving Super: only add to Super's bonus_balance.
"""
from decimal import Decimal
from django.utils import timezone

from core.models import (
    UserRole,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)
from core.notification_utils import notify_player_approval


def approve_bonus_request(bonus_request, processed_by, pin=None, use_password=False):
    """
    Approve a bonus request. For powerhouse->super: only add to super's bonus_balance.
    For others: deduct parent main_balance, add to user bonus_balance.
    Returns (True, None) or (False, error_message).
    """
    user = bonus_request.user
    amount = bonus_request.amount
    if user.role == UserRole.SUPER and processed_by.role == UserRole.POWERHOUSE:
        user.bonus_balance = (user.bonus_balance or Decimal('0')) + amount
        user.save(update_fields=['bonus_balance'])
        bonus_request.status = 'approved'
        bonus_request.processed_by = processed_by
        bonus_request.processed_at = timezone.now()
        bonus_request.save(update_fields=['status', 'processed_by', 'processed_at'])
        Transaction.objects.create(
            user=user,
            action_type=TransactionActionType.IN,
            wallet=TransactionWallet.BONUS_BALANCE,
            transaction_type=TransactionType.BONUS,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            remarks=f'Bonus request #{bonus_request.pk} approved',
        )
        if user.role == UserRole.PLAYER:
            notify_player_approval(user, processed_by, f'Your bonus request of ₹{amount} has been approved.')
        return True, None
    parent = user.parent
    if not parent:
        return False, 'User has no parent'
    if (parent.main_balance or Decimal('0')) < amount:
        return False, 'Parent has insufficient balance'
    parent.main_balance = (parent.main_balance or Decimal('0')) - amount
    parent.save(update_fields=['main_balance'])
    user.bonus_balance = (user.bonus_balance or Decimal('0')) + amount
    user.save(update_fields=['bonus_balance'])
    bonus_request.status = 'approved'
    bonus_request.processed_by = processed_by
    bonus_request.processed_at = timezone.now()
    bonus_request.save(update_fields=['status', 'processed_by', 'processed_at'])
    Transaction.objects.create(
        user=parent,
        action_type=TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.BONUS,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        to_user=user,
        remarks=f'Bonus request #{bonus_request.pk} for {user.username}',
    )
    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.BONUS_BALANCE,
        transaction_type=TransactionType.BONUS,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=parent,
        remarks=f'Bonus request #{bonus_request.pk} approved',
    )
    if user.role == UserRole.PLAYER:
        notify_player_approval(user, processed_by, f'Your bonus request of ₹{amount} has been approved.')
    return True, None
