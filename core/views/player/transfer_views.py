from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from core.permissions import require_role
from core.models import User, UserRole, Transaction, TransactionActionType, TransactionWallet, TransactionType, TransactionStatus

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    if not request.user.check_password(request.data.get('password', '')):
        return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    to_user = User.objects.filter(username=request.data.get('username')).first()
    if not to_user: return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    try: amount = Decimal(str(request.data.get('amount', 0)))
    except: return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0: return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
    if (request.user.main_balance or 0) < amount: return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)
    request.user.main_balance = (request.user.main_balance or Decimal('0')) - amount
    request.user.save(update_fields=['main_balance'])
    to_user.main_balance = (to_user.main_balance or Decimal('0')) + amount
    to_user.save(update_fields=['main_balance'])
    Transaction.objects.create(user=request.user, action_type=TransactionActionType.OUT, wallet=TransactionWallet.MAIN_BALANCE, transaction_type=TransactionType.TRANSFER, amount=amount, status=TransactionStatus.SUCCESS, to_user=to_user, remarks='Transfer')
    Transaction.objects.create(user=to_user, action_type=TransactionActionType.IN, wallet=TransactionWallet.MAIN_BALANCE, transaction_type=TransactionType.TRANSFER, amount=amount, status=TransactionStatus.SUCCESS, from_user=request.user, remarks='Transfer')
    return Response({'detail': 'OK'})
