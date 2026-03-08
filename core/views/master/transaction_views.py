from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from core.permissions import require_role
from core.models import Transaction, UserRole
from core.serializers import TransactionSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err: return err
    qs = Transaction.objects.filter(Q(user__parent=request.user) | Q(user=request.user)).select_related('user').order_by('-created_at')[:500]
    return Response(TransactionSerializer(qs, many=True).data)
