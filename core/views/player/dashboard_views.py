from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import UserRole, Transaction
from core.serializers import TransactionSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    u = request.user
    recent_tx = Transaction.objects.filter(user=u).order_by('-created_at')[:10]
    return Response({
        'main_balance': str(u.main_balance or 0),
        'bonus_balance': str(u.bonus_balance or 0),
        'recent_transactions': TransactionSerializer(recent_tx, many=True).data,
    })

