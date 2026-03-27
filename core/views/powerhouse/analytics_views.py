"""Powerhouse analytics: overview, games, finance, customers, per-user."""
from datetime import timedelta, date as date_type
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import (
    User, UserRole,
    Deposit, Withdraw,
    GameLog, Transaction,
    ActivityLog, ActivityAction,
    Game, GameProvider,
    RequestStatus,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_date(s):
    if not s or not s.strip():
        return None
    try:
        return timezone.datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _date_range(request):
    """Return (date_from, date_to) with sensible defaults (last 30 days)."""
    today = timezone.now().date()
    date_from = _parse_date(request.query_params.get("date_from")) or (today - timedelta(days=29))
    date_to = _parse_date(request.query_params.get("date_to")) or today
    return date_from, date_to


def _str(v):
    return str(v) if v is not None else "0"


def _day_series(date_from, date_to, qs_factory):
    """Build a [{date, **values}] list from date_from to date_to."""
    delta = (date_to - date_from).days
    series = []
    for i in range(delta + 1):
        d = date_from + timedelta(days=i)
        entry = {"date": d.isoformat()}
        entry.update(qs_factory(d))
        series.append(entry)
    return series


# ── 1. Overview ───────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _date_range(request)

    # Deposits / Withdrawals (approved only for financials)
    dep_qs = Deposit.objects.filter(
        created_at__date__range=[date_from, date_to],
        status=RequestStatus.APPROVED,
    )
    wd_qs = Withdraw.objects.filter(
        created_at__date__range=[date_from, date_to],
        status=RequestStatus.APPROVED,
    )
    total_deposits = dep_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    total_withdrawals = wd_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    # GameLog aggregates
    gl_qs = GameLog.objects.filter(created_at__date__range=[date_from, date_to])
    gl_agg = gl_qs.aggregate(
        total_bet=Sum("bet_amount"),
        total_win=Sum("win_amount"),
    )
    total_bet = gl_agg["total_bet"] or Decimal("0")
    total_win = gl_agg["total_win"] or Decimal("0")
    platform_pl = total_bet - total_win

    # Active players (placed at least one bet)
    active_users = gl_qs.values("user_id").distinct().count()

    # New registrations
    new_registrations = User.objects.filter(
        role=UserRole.PLAYER,
        date_joined__date__range=[date_from, date_to],
    ).count()

    # Daily series
    def _day(d):
        dq = Deposit.objects.filter(created_at__date=d, status=RequestStatus.APPROVED)
        wq = Withdraw.objects.filter(created_at__date=d, status=RequestStatus.APPROVED)
        gq = GameLog.objects.filter(created_at__date=d)
        g = gq.aggregate(tb=Sum("bet_amount"), tw=Sum("win_amount"))
        tb = g["tb"] or Decimal("0")
        tw = g["tw"] or Decimal("0")
        return {
            "deposits": _str(dq.aggregate(s=Sum("amount"))["s"] or 0),
            "withdrawals": _str(wq.aggregate(s=Sum("amount"))["s"] or 0),
            "bets": _str(tb),
            "pl": _str(tb - tw),
            "active_users": gq.values("user_id").distinct().count(),
        }

    series = _day_series(date_from, date_to, _day)

    return Response({
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_deposits": _str(total_deposits),
        "total_withdrawals": _str(total_withdrawals),
        "revenue": _str(total_deposits - total_withdrawals),
        "total_bet": _str(total_bet),
        "platform_pl": _str(platform_pl),
        "active_users": active_users,
        "new_registrations": new_registrations,
        "series": series,
    })


# ── 2. Game Analytics ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_analytics(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _date_range(request)

    gl_qs = GameLog.objects.filter(created_at__date__range=[date_from, date_to])

    # Top 10 games by bet volume
    top_games = (
        gl_qs.values("game__id", "game__name")
        .annotate(
            total_bet=Sum("bet_amount"),
            total_win=Sum("win_amount"),
            play_count=Count("id"),
        )
        .order_by("-total_bet")[:10]
    )
    top_games_list = [
        {
            "game_id": r["game__id"],
            "game_name": r["game__name"] or "Unknown",
            "total_bet": _str(r["total_bet"] or 0),
            "total_win": _str(r["total_win"] or 0),
            "pl": _str((r["total_bet"] or Decimal("0")) - (r["total_win"] or Decimal("0"))),
            "play_count": r["play_count"],
        }
        for r in top_games
    ]

    # Provider breakdown
    provider_breakdown = (
        gl_qs.values("provider__id", "provider__name")
        .annotate(
            total_bet=Sum("bet_amount"),
            total_win=Sum("win_amount"),
            play_count=Count("id"),
        )
        .order_by("-total_bet")
    )
    provider_list = [
        {
            "provider_id": r["provider__id"],
            "provider_name": r["provider__name"] or "Unknown",
            "total_bet": _str(r["total_bet"] or 0),
            "total_win": _str(r["total_win"] or 0),
            "pl": _str((r["total_bet"] or Decimal("0")) - (r["total_win"] or Decimal("0"))),
            "play_count": r["play_count"],
        }
        for r in provider_breakdown
    ]

    # Category breakdown (via game__category)
    category_breakdown = (
        gl_qs.values("game__category__id", "game__category__name")
        .annotate(total_bet=Sum("bet_amount"), play_count=Count("id"))
        .order_by("-total_bet")
    )
    category_list = [
        {
            "category_id": r["game__category__id"],
            "category_name": r["game__category__name"] or "Unknown",
            "total_bet": _str(r["total_bet"] or 0),
            "play_count": r["play_count"],
        }
        for r in category_breakdown
    ]

    return Response({
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "top_games": top_games_list,
        "providers": provider_list,
        "categories": category_list,
    })


# ── 3. Finance & P/L ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def finance_analytics(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _date_range(request)

    dep_qs = Deposit.objects.filter(created_at__date__range=[date_from, date_to])
    wd_qs = Withdraw.objects.filter(created_at__date__range=[date_from, date_to])

    dep_approved = dep_qs.filter(status=RequestStatus.APPROVED)
    wd_approved = wd_qs.filter(status=RequestStatus.APPROVED)

    total_deposits = dep_approved.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    total_withdrawals = wd_approved.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    # Bonus-related transactions
    from core.models import Transaction, TransactionType
    bonus_tx = Transaction.objects.filter(
        transaction_type=TransactionType.BONUS,
        created_at__date__range=[date_from, date_to],
    )
    total_bonus = bonus_tx.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    bonus_count = bonus_tx.count()

    # GameLog P/L
    gl_agg = GameLog.objects.filter(
        created_at__date__range=[date_from, date_to]
    ).aggregate(tb=Sum("bet_amount"), tw=Sum("win_amount"))
    total_bet = gl_agg["tb"] or Decimal("0")
    total_win = gl_agg["tw"] or Decimal("0")
    game_pl = total_bet - total_win

    # Daily D/W series
    def _day(d):
        dq = Deposit.objects.filter(created_at__date=d, status=RequestStatus.APPROVED)
        wq = Withdraw.objects.filter(created_at__date=d, status=RequestStatus.APPROVED)
        gq = GameLog.objects.filter(created_at__date=d)
        ga = gq.aggregate(tb=Sum("bet_amount"), tw=Sum("win_amount"))
        tb = ga["tb"] or Decimal("0")
        tw = ga["tw"] or Decimal("0")
        ds = dq.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        ws = wq.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        return {
            "deposits": _str(ds),
            "withdrawals": _str(ws),
            "net": _str(ds - ws),
            "game_pl": _str(tb - tw),
        }

    series = _day_series(date_from, date_to, _day)

    # Top depositors
    top_depositors = (
        dep_approved.values("user__id", "user__username")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:10]
    )
    top_dep_list = [
        {
            "user_id": r["user__id"],
            "username": r["user__username"],
            "total": _str(r["total"] or 0),
            "count": r["count"],
        }
        for r in top_depositors
    ]

    # Top withdrawers
    top_withdrawers = (
        wd_approved.values("user__id", "user__username")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:10]
    )
    top_wd_list = [
        {
            "user_id": r["user__id"],
            "username": r["user__username"],
            "total": _str(r["total"] or 0),
            "count": r["count"],
        }
        for r in top_withdrawers
    ]

    return Response({
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_deposits": _str(total_deposits),
        "total_withdrawals": _str(total_withdrawals),
        "net_cash_flow": _str(total_deposits - total_withdrawals),
        "total_bonus_paid": _str(total_bonus),
        "bonus_count": bonus_count,
        "game_pl": _str(game_pl),
        "series": series,
        "top_depositors": top_dep_list,
        "top_withdrawers": top_wd_list,
    })


# ── 4. Customer Behaviour ─────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_analytics(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _date_range(request)

    act_qs = ActivityLog.objects.filter(created_at__date__range=[date_from, date_to])

    # DAU series
    def _day(d):
        logins = act_qs.filter(action=ActivityAction.LOGIN, created_at__date=d)
        return {
            "dau": logins.values("user_id").distinct().count(),
            "logins": logins.count(),
        }

    series = _day_series(date_from, date_to, _day)

    # Top players by bet volume
    gl_qs = GameLog.objects.filter(created_at__date__range=[date_from, date_to])
    top_players = (
        gl_qs.values("user__id", "user__username")
        .annotate(total_bet=Sum("bet_amount"), play_count=Count("id"))
        .order_by("-total_bet")[:10]
    )
    top_players_list = [
        {
            "user_id": r["user__id"],
            "username": r["user__username"],
            "total_bet": _str(r["total_bet"] or 0),
            "play_count": r["play_count"],
        }
        for r in top_players
    ]

    # Device breakdown
    device_qs = (
        act_qs.exclude(device="")
        .values("device")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    device_breakdown = [{"device": r["device"], "count": r["count"]} for r in device_qs]

    # New vs returning players (registered in range vs before)
    new_players = User.objects.filter(
        role=UserRole.PLAYER,
        date_joined__date__range=[date_from, date_to],
    ).count()
    total_players = User.objects.filter(role=UserRole.PLAYER).count()

    return Response({
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_players": total_players,
        "new_players": new_players,
        "series": series,
        "top_players": top_players_list,
        "device_breakdown": device_breakdown,
    })


# ── 5. Per-user Analytics ────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_analytics(request, user_id):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    try:
        player = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=404)

    date_from, date_to = _date_range(request)

    # Bet summary
    gl_qs = GameLog.objects.filter(user=player, created_at__date__range=[date_from, date_to])
    gl_agg = gl_qs.aggregate(
        total_bet=Sum("bet_amount"),
        total_win=Sum("win_amount"),
        play_count=Count("id"),
    )
    total_bet = gl_agg["total_bet"] or Decimal("0")
    total_win = gl_agg["total_win"] or Decimal("0")

    # Recent game history
    recent_bets = gl_qs.select_related("game", "provider").order_by("-created_at")[:20]
    bet_history = [
        {
            "id": g.id,
            "game": g.game.name if g.game_id else None,
            "provider": g.provider.name if g.provider_id else None,
            "type": g.type,
            "bet_amount": _str(g.bet_amount),
            "win_amount": _str(g.win_amount),
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
        for g in recent_bets
    ]

    # Transaction history
    tx_qs = Transaction.objects.filter(
        user=player,
        created_at__date__range=[date_from, date_to],
    ).order_by("-created_at")[:30]
    tx_history = [
        {
            "id": t.id,
            "transaction_type": t.transaction_type,
            "action_type": t.action_type,
            "wallet": t.wallet,
            "amount": _str(t.amount),
            "status": t.status,
            "balance_before": _str(t.balance_before) if t.balance_before is not None else None,
            "balance_after": _str(t.balance_after) if t.balance_after is not None else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tx_qs
    ]

    # Activity timeline
    act_qs = ActivityLog.objects.filter(
        user=player,
        created_at__date__range=[date_from, date_to],
    ).order_by("-created_at")[:30]
    activity = [
        {
            "id": a.id,
            "action": a.action,
            "ip": a.ip,
            "device": a.device,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in act_qs
    ]

    # Daily balance trend (from transactions, latest balance_after per day)
    balance_series = []
    for i in range((date_to - date_from).days + 1):
        d = date_from + timedelta(days=i)
        last_tx = (
            Transaction.objects.filter(user=player, created_at__date=d, balance_after__isnull=False)
            .order_by("-created_at")
            .first()
        )
        balance_series.append({
            "date": d.isoformat(),
            "balance": _str(last_tx.balance_after) if last_tx else None,
        })

    return Response({
        "user_id": player.id,
        "username": player.username,
        "date_joined": player.date_joined.isoformat() if player.date_joined else None,
        "is_active": player.is_active,
        "main_balance": _str(player.main_balance),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_bet": _str(total_bet),
        "total_win": _str(total_win),
        "net_pl": _str(total_bet - total_win),
        "play_count": gl_agg["play_count"] or 0,
        "bet_history": bet_history,
        "transactions": tx_history,
        "activity": activity,
        "balance_series": balance_series,
    })
