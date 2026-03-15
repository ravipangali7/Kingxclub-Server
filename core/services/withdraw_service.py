"""Withdraw approval: user deducted, parent added. Player must have at least one approved payment mode (parent's)."""
from decimal import Decimal
from django.utils import timezone
from core.models import (
    UserRole,
    Withdraw,
    WithdrawWallet,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)
from core.notification_utils import notify_player_approval
from core.services.withdraw_eligibility import get_withdraw_eligibility


def approve_withdraw(withdrawal, processed_by, pin=None, use_password=False):
    user = withdrawal.user
    amount = withdrawal.amount
    if user.role == UserRole.SUPER and processed_by.role == UserRole.POWERHOUSE:
        if (user.main_balance or Decimal('0')) < amount:
            return False, 'Insufficient balance'
        user.main_balance = (user.main_balance or Decimal('0')) - amount
        user.save(update_fields=['main_balance'])
        withdrawal.status = 'approved'
        withdrawal.processed_by = processed_by
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'processed_by', 'processed_at'])
        Transaction.objects.create(
            user=user,
            action_type=TransactionActionType.OUT,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.WITHDRAW,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            remarks='Withdraw approved',
            processed_by=processed_by,
        )
        if user.role == UserRole.PLAYER:
            notify_player_approval(user, processed_by, f'Your withdrawal of ₹{amount} has been approved.')
        return True, None
    parent = user.parent
    if not parent:
        return False, 'User has no parent'
    if user.role == UserRole.PLAYER:
        # Re-check eligibility at approval time (player only; wallet = main or bonus)
        wallet = getattr(withdrawal, 'wallet', None) or WithdrawWallet.MAIN
        eligibility = get_withdraw_eligibility(user)
        if wallet == WithdrawWallet.BONUS:
            if not eligibility['can_withdraw_bonus']:
                return False, 'Bonus is not withdrawable until bonus roll requirement is met.'
            if amount > eligibility['bonus_withdrawable']:
                return False, 'Insufficient bonus balance.'
            user.bonus_balance = (user.bonus_balance or Decimal('0')) - amount
            user.save(update_fields=['bonus_balance'])
            out_wallet = TransactionWallet.BONUS_BALANCE
        else:
            staff_bypass = processed_by.role in (UserRole.SUPER, UserRole.MASTER, UserRole.POWERHOUSE)
            if not staff_bypass and not eligibility['can_withdraw_main']:
                return False, 'Main balance is not withdrawable until at least one game is played after deposit.'
            main_balance = user.main_balance or Decimal('0')
            if amount > main_balance:
                return False, 'Insufficient balance'
            if not staff_bypass and amount > eligibility['main_withdrawable']:
                return False, 'Insufficient balance'
            user.main_balance = main_balance - amount
            user.save(update_fields=['main_balance'])
            out_wallet = TransactionWallet.MAIN_BALANCE
    else:
        # Non-player (e.g. master): main only
        if (user.main_balance or Decimal('0')) < amount:
            return False, 'Insufficient balance'
        user.main_balance = (user.main_balance or Decimal('0')) - amount
        user.save(update_fields=['main_balance'])
        out_wallet = TransactionWallet.MAIN_BALANCE
    parent.main_balance = (parent.main_balance or Decimal('0')) + amount
    parent.save(update_fields=['main_balance'])
    withdrawal.status = 'approved'
    withdrawal.processed_by = processed_by
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=['status', 'processed_by', 'processed_at'])
    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.OUT,
        wallet=out_wallet,
        transaction_type=TransactionType.WITHDRAW,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        remarks='Withdraw approved',
        processed_by=processed_by,
    )
    Transaction.objects.create(
        user=parent,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.WITHDRAW,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=user,
        remarks='Withdraw from ' + user.username,
        processed_by=processed_by,
    )
    if user.role == UserRole.PLAYER:
        notify_player_approval(user, processed_by, f'Your withdrawal of ₹{amount} has been approved.')
    return True, None
