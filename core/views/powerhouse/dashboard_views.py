"""Powerhouse dashboard: aggregates, recent activity, date range, series."""
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum

from core.permissions import require_role
from core.models import User, UserRole, Deposit, Withdraw, BonusRequest


def _parse_date(s):
    if not s or not s.strip():
        return None
    try:
        return timezone.datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    now = timezone.now()
    today = now.date()

    date_from = _parse_date(request.query_params.get('date_from'))
    date_to = _parse_date(request.query_params.get('date_to'))

    pending_deposits = Deposit.objects.filter(status='pending').count()
    pending_withdrawals = Withdraw.objects.filter(status='pending').count()
    pending_bonus_requests = BonusRequest.objects.filter(status='pending').count()
    players = User.objects.filter(role=UserRole.PLAYER).count()
    masters = User.objects.filter(role=UserRole.MASTER).count()
    supers = User.objects.filter(role=UserRole.SUPER).count()
    total_balance = sum(
        (u.main_balance or 0) for u in User.objects.filter(role=UserRole.PLAYER)
    )

    # Today aggregates
    deposits_today = Deposit.objects.filter(created_at__date=today)
    deposits_today_count = deposits_today.count()
    deposits_today_sum = deposits_today.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    withdrawals_today = Withdraw.objects.filter(created_at__date=today)
    withdrawals_today_count = withdrawals_today.count()
    withdrawals_today_sum = withdrawals_today.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    # Players added in last 7 days
    from datetime import timedelta
    week_ago = now - timedelta(days=7)
    players_added_7d = User.objects.filter(role=UserRole.PLAYER, created_at__gte=week_ago).count()

    # Recent deposits (last 10)
    recent_dep_qs = Deposit.objects.select_related('user').order_by('-created_at')[:10]
    recent_deposits = [
        {
            'id': d.id,
            'username': d.user.username if d.user_id else None,
            'user_username': d.user.username if d.user_id else None,
            'amount': str(d.amount),
            'status': d.status,
            'created_at': d.created_at.isoformat() if d.created_at else None,
        }
        for d in recent_dep_qs
    ]

    # Recent withdrawals (last 10)
    recent_wd_qs = Withdraw.objects.select_related('user').order_by('-created_at')[:10]
    recent_withdrawals = [
        {
            'id': w.id,
            'username': w.user.username if w.user_id else None,
            'user_username': w.user.username if w.user_id else None,
            'amount': str(w.amount),
            'status': w.status,
            'created_at': w.created_at.isoformat() if w.created_at else None,
        }
        for w in recent_wd_qs
    ]

    # Last 7 days daily series for charts
    series_7d = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        dep_day = Deposit.objects.filter(created_at__date=d)
        wd_day = Withdraw.objects.filter(created_at__date=d)
        series_7d.append({
            'date': d.isoformat(),
            'deposits_count': dep_day.count(),
            'deposits_sum': str(dep_day.aggregate(s=Sum('amount'))['s'] or Decimal('0')),
            'withdrawals_count': wd_day.count(),
            'withdrawals_sum': str(wd_day.aggregate(s=Sum('amount'))['s'] or Decimal('0')),
        })

    payload = {
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'pending_bonus_requests': pending_bonus_requests,
        'total_players': players,
        'total_masters': masters,
        'total_supers': supers,
        'total_balance': str(total_balance),
        'recent_deposits': recent_deposits,
        'recent_withdrawals': recent_withdrawals,
        'deposits_today_count': deposits_today_count,
        'deposits_today_sum': str(deposits_today_sum),
        'withdrawals_today_count': withdrawals_today_count,
        'withdrawals_today_sum': str(withdrawals_today_sum),
        'players_added_7d': players_added_7d,
        'series_7d': series_7d,
    }
    return Response(payload)
