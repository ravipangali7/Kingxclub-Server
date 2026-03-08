from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import User, UserRole, Deposit, Withdraw, BonusRequest


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    masters = User.objects.filter(parent=request.user, role=UserRole.MASTER).count()
    players = User.objects.filter(parent__parent=request.user, role=UserRole.PLAYER).count()
    pending_d = Deposit.objects.filter(status='pending').count()
    pending_w = Withdraw.objects.filter(status='pending').count()
    pending_br = BonusRequest.objects.filter(
        Q(user__parent=request.user) | Q(user__parent__parent=request.user),
        status='pending'
    ).count()
    return Response({
        'pending_deposits': pending_d,
        'pending_withdrawals': pending_w,
        'pending_bonus_requests': pending_br,
        'total_masters': masters,
        'total_players': players,
        'recent_deposits': [],
        'recent_withdrawals': [],
    })
