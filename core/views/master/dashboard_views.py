from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import User, UserRole, Deposit, Withdraw, BonusRequest

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    err = require_role(request, [UserRole.MASTER])
    if err: return err
    players = User.objects.filter(parent=request.user, role=UserRole.PLAYER).count()
    pd = Deposit.objects.filter(user__parent=request.user, status='pending').count()
    pw = Withdraw.objects.filter(user__parent=request.user, status='pending').count()
    pbr = BonusRequest.objects.filter(user__parent=request.user, status='pending').count()
    return Response({'pending_deposits': pd, 'pending_withdrawals': pw, 'pending_bonus_requests': pbr, 'total_players': players, 'recent_deposits': [], 'recent_withdrawals': []})
