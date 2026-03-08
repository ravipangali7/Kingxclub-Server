from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import GameLog, Transaction, UserRole
from core.serializers import GameLogSerializer, TransactionSerializer


def _get_related_transaction(game_log):
    if hasattr(game_log, 'transactions') and game_log.transactions.exists():
        return game_log.transactions.first()
    return Transaction.objects.filter(
        user=game_log.user,
        remarks=f"Game round {game_log.round}",
    ).first()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err: return err
    qs = GameLog.objects.filter(user__parent=request.user).select_related('user', 'game', 'provider').order_by('-created_at')[:500]
    return Response(GameLogSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_detail(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    log = GameLog.objects.filter(user__parent=request.user, pk=pk).select_related('user', 'game', 'provider').first()
    if not log:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    tx = _get_related_transaction(log)
    return Response({
        'game_log': GameLogSerializer(log).data,
        'transaction': TransactionSerializer(tx).data if tx else None,
    })
