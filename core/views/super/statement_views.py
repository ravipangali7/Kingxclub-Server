"""Account and Bonus statement listing for super (date range, pagination)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from core.permissions import require_role
from core.models import Transaction, UserRole
from core.models import TransactionActionType, TransactionType


def _parse_dates(request):
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    return date_from, date_to


def _base_qs(request):
    if request.user.role in (UserRole.POWERHOUSE, getattr(UserRole.POWERHOUSE, "value", "powerhouse")):
        return Transaction.objects.all().select_related("user").order_by("-created_at")
    return Transaction.objects.filter(
        Q(user__parent=request.user)
        | Q(user__parent__parent=request.user)
        | Q(user=request.user)
    ).select_related("user").order_by("-created_at")


def _to_statement_row(tx):
    debit = str(tx.amount) if tx.action_type == TransactionActionType.OUT else "0"
    credit = str(tx.amount) if tx.action_type == TransactionActionType.IN else "0"
    balance = str(tx.balance_after) if tx.balance_after is not None else ""
    return {
        "id": tx.id,
        "username": tx.user.username if tx.user_id else "",
        "transaction_id": tx.id,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "description": tx.remarks or "",
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_statement_list(request):
    err = require_role(request, [UserRole.SUPER, UserRole.POWERHOUSE])
    if err:
        return err
    date_from, date_to = _parse_dates(request)
    qs = _base_qs(request)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    count = qs.count()
    start = (page - 1) * page_size
    rows = qs[start : start + page_size]
    results = [_to_statement_row(tx) for tx in rows]
    return Response({"results": results, "count": count})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bonus_statement_list(request):
    err = require_role(request, [UserRole.SUPER, UserRole.POWERHOUSE])
    if err:
        return err
    date_from, date_to = _parse_dates(request)
    qs = _base_qs(request).filter(transaction_type=TransactionType.BONUS)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    count = qs.count()
    start = (page - 1) * page_size
    rows = qs[start : start + page_size]
    results = [_to_statement_row(tx) for tx in rows]
    return Response({"results": results, "count": count})
