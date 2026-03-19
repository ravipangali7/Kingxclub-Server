from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from django.db import transaction as db_transaction
from core.permissions import require_role
from core.models import User, UserRole, Transaction, TransactionActionType, TransactionWallet, TransactionType, TransactionStatus

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer(request):
    allowed_roles = [UserRole.POWERHOUSE, UserRole.SUPER, UserRole.MASTER, UserRole.PLAYER]
    err = require_role(request, allowed_roles)
    if err:
        return err

    if not request.user.check_password(request.data.get('password', '')):
        return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)

    recipient_username = (request.data.get('username') or '').strip()
    to_user = User.objects.filter(username=recipient_username).first()
    if not to_user:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    if to_user.id == request.user.id:
        return Response({'detail': 'Cannot transfer to yourself.'}, status=status.HTTP_400_BAD_REQUEST)
    if to_user.role not in allowed_roles:
        return Response({'detail': 'Invalid receiver role.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = Decimal(str(request.data.get('amount', 0)))
    except Exception:
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    with db_transaction.atomic():
        locked_users = User.objects.select_for_update().filter(id__in=[request.user.id, to_user.id])
        user_by_id = {u.id: u for u in locked_users}
        from_user = user_by_id.get(request.user.id)
        receiver = user_by_id.get(to_user.id)
        if not from_user or not receiver:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        sender_before = from_user.main_balance or Decimal('0')
        receiver_before = receiver.main_balance or Decimal('0')
        if sender_before < amount:
            return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

        sender_after = sender_before - amount
        receiver_after = receiver_before + amount

        from_user.main_balance = sender_after
        from_user.save(update_fields=['main_balance'])

        receiver.main_balance = receiver_after
        receiver.save(update_fields=['main_balance'])

        Transaction.objects.create(
            user=from_user,
            action_type=TransactionActionType.OUT,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            from_user=from_user,
            to_user=receiver,
            balance_before=sender_before,
            balance_after=sender_after,
            remarks=f'Transfer to {receiver.username}',
        )
        Transaction.objects.create(
            user=receiver,
            action_type=TransactionActionType.IN,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            from_user=from_user,
            to_user=receiver,
            balance_before=receiver_before,
            balance_after=receiver_after,
            remarks=f'Transfer from {from_user.username}',
        )

    return Response({'detail': 'Transfer successful.'})
