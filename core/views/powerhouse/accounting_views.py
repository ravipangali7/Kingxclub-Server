"""Accounting report for powerhouse: date-scoped summary, game logs, transactions, deposits, withdrawals."""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q, Sum, F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import (
    GameLog,
    Transaction,
    Deposit,
    Withdraw,
    UserRole,
)
from core.serializers import (
    GameLogSerializer,
    TransactionSerializer,
    DepositSerializer,
    WithdrawSerializer,
)


def _parse_date_range(request):
    """Return (date_from, date_to) as date objects. Default to today if missing."""
    today = timezone.now().date()
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    if not date_from or not date_to:
        return today, today
    try:
        from datetime import datetime
        df = datetime.strptime(date_from, "%Y-%m-%d").date()
        dt = datetime.strptime(date_to, "%Y-%m-%d").date()
        return df, dt
    except (ValueError, TypeError):
        return today, today


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accounting_report(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    date_from, date_to = _parse_date_range(request)

    # Powerhouse sees all: scope to players for game logs; all for deposits/withdrawals/transactions
    game_log_user_filter = Q(user__role=UserRole.PLAYER)
    base_user_filter = Q(user__role=UserRole.PLAYER) | Q(user=request.user)

    # Game logs in range (players only)
    game_logs_qs = (
        GameLog.objects.filter(game_log_user_filter)
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .select_related("user", "game", "provider")
        .order_by("-created_at")
    )
    game_logs = GameLogSerializer(game_logs_qs, many=True).data

    # P/L: sum(win_amount - lose_amount) from GameLog in range
    pl_agg = game_logs_qs.aggregate(
        total=Sum(F("win_amount") - F("lose_amount"))
    )
    total_pl = pl_agg.get("total")
    if total_pl is None:
        total_pl = Decimal("0")

    # Transactions in range
    tx_qs = (
        Transaction.objects.filter(base_user_filter)
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .select_related("user")
        .order_by("-created_at")
    )
    transactions = TransactionSerializer(tx_qs, many=True).data

    # Deposits in range (all)
    dep_qs = (
        Deposit.objects.all()
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .select_related("user", "payment_mode")
        .order_by("-created_at")
    )
    deposits = DepositSerializer(dep_qs, many=True, context={"request": request}).data
    deposits_approved = dep_qs.filter(status="approved")
    total_deposits = deposits_approved.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    deposits_count = dep_qs.count()

    # Withdrawals in range (all)
    wd_qs = (
        Withdraw.objects.all()
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .select_related("user", "payment_mode")
        .order_by("-created_at")
    )
    withdrawals = WithdrawSerializer(wd_qs, many=True, context={"request": request}).data
    withdrawals_approved = wd_qs.filter(status="approved")
    total_withdrawals = withdrawals_approved.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    withdrawals_count = wd_qs.count()

    summary = {
        "total_pl": str(total_pl),
        "total_deposits": str(total_deposits),
        "deposits_count": deposits_count,
        "total_withdrawals": str(total_withdrawals),
        "withdrawals_count": withdrawals_count,
        "game_logs_count": len(game_logs),
        "transactions_count": len(transactions),
    }

    return Response({
        "summary": summary,
        "game_logs": game_logs,
        "transactions": transactions,
        "deposits": deposits,
        "withdrawals": withdrawals,
    })
