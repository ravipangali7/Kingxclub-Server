"""Reports for master: Total D/W (deposit/withdrawal by user)."""
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum
from core.permissions import require_role, get_players_queryset
from core.models import Deposit, Withdraw, UserRole


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def total_dw_list(request):
    """List per-user deposit/withdrawal totals (master's players). date_from, date_to."""
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    players = get_players_queryset(request.user)
    results = []
    for user in players:
        dep_qs = Deposit.objects.filter(user=user, status="approved")
        wd_qs = Withdraw.objects.filter(user=user, status="approved")
        if date_from:
            dep_qs = dep_qs.filter(created_at__date__gte=date_from)
            wd_qs = wd_qs.filter(created_at__date__gte=date_from)
        if date_to:
            dep_qs = dep_qs.filter(created_at__date__lte=date_to)
            wd_qs = wd_qs.filter(created_at__date__lte=date_to)
        total_dep = dep_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total_wd = wd_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total = total_dep - total_wd
        results.append({
            "username": user.username,
            "user_id": user.id,
            "deposit": str(total_dep),
            "withdrawal": str(total_wd),
            "total": str(total),
        })
    return Response(results)
