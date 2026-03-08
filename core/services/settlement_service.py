"""Settlement: Super settles a master - master pl_balance to 0, master main_balance to super."""
from decimal import Decimal
from django.utils import timezone
from core.models import (
    User,
    UserRole,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)


def settle_master(master, super_user, pin=None):
    """
    Super settles a master: master pl_balance -> 0, master main_balance added to super main_balance, master main_balance -> 0.
    Returns (True, None) or (False, error_message).
    """
    if super_user.role != UserRole.SUPER or master.role != UserRole.MASTER or master.parent_id != super_user.id:
        return False, 'Invalid settlement'
    amount = master.main_balance or Decimal('0')
    super_user.main_balance = (super_user.main_balance or Decimal('0')) + amount
    super_user.save(update_fields=['main_balance'])
    master.main_balance = Decimal('0')
    master.pl_balance = Decimal('0')
    master.save(update_fields=['main_balance', 'pl_balance'])
    Transaction.objects.create(
        user=master,
        action_type=TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.SETTLEMENT,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        to_user=super_user,
        remarks='Settlement to super',
    )
    Transaction.objects.create(
        user=super_user,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.SETTLEMENT,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=master,
        remarks=f'Settlement from master {master.username}',
    )
    return True, None
