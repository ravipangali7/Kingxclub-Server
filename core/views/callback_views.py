"""
Provider game callback: POST from provider with round result; update user balance, GameLog, master PL.
Accepts both application/x-www-form-urlencoded and application/json bodies.
"""
import json
import logging
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse

from core.models import (
    SuperSetting,
    User,
    UserRole,
    Game,
    GameProvider,
    GameCategory,
    GameLog,
    GameLogWallet,
    GameLogType,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)


def _get_user_by_mobile(mobile):
    """Resolve User by mobile (user_id from provider): username or id."""
    if not mobile:
        return None
    mobile = str(mobile).strip()
    user = User.objects.filter(username=mobile).first()
    if user:
        return user
    try:
        pk = int(mobile)
        return User.objects.filter(pk=pk).first()
    except (ValueError, TypeError):
        pass
    return None


def _get_or_create_game_and_provider(game_uid):
    """Resolve Game by game_uid; if not found, create placeholder provider/game."""
    game = Game.objects.filter(game_uid=game_uid).select_related("provider", "category").first()
    if game:
        return game
    cat, _ = GameCategory.objects.get_or_create(
        name="Other",
        defaults={"is_active": True},
    )
    prov, _ = GameProvider.objects.get_or_create(
        code="callback_unknown",
        defaults={"name": "Unknown (Callback)", "is_active": True},
    )
    game = Game.objects.create(
        provider=prov,
        category=cat,
        name=game_uid[:255],
        game_uid=game_uid,
        is_active=True,
    )
    return game


def _get_callback_data(request):
    """
    Return a dict of callback fields from either JSON body or request.POST.
    Same field names: mobile, user_id, bet_amount, win_amount, game_uid, game_round,
    token, wallet_before, wallet_after, change, timestamp.
    """
    print("---------------------- Call BACK ----------------------")
    print(request.body)
    print("---------------------- ENDCall BACK ----------------------")
    content_type = (request.content_type or "").strip().split(";")[0].lower()
    if content_type == "application/json":
        try:
            body = request.body.decode("utf-8") if request.body else "{}"
            return json.loads(body) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    # form-encoded or other: use POST
    return request.POST.dict() if hasattr(request.POST, "dict") else dict(request.POST)


def _is_bonus_game_wallet(user):
    return (getattr(user, "game_wallet", "main") or "main") == "bonus"


def _save_wallet_after(user, wallet_after):
    if _is_bonus_game_wallet(user):
        user.bonus_balance = wallet_after
        user.save(update_fields=["bonus_balance"])
        return
    user.main_balance = wallet_after
    user.save(update_fields=["main_balance"])


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def game_callback(request):
    """
    Public endpoint (no auth, no CSRF). Game provider POSTs round results here.
    GET: return info so you can verify this URL is reachable (use this URL in provider dashboard).
    OPTIONS: return 200 with Allow header for preflight if needed.
    POST from provider: mobile, bet_amount, win_amount, game_uid, game_round, token,
    wallet_before, wallet_after, change, timestamp, currency_code.
    Accepts form-encoded or application/json body.
    Update user balance to wallet_after, create/update GameLog, update master pl_balance.
    Return JSON {"status": "ok"}.
    """
    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Allow"] = "GET, POST, OPTIONS"
        return response
    if request.method == "GET":
        return JsonResponse({
            "message": "Game callback endpoint. Configure your game provider to POST round results here.",
            "method": "POST",
            "fields": ["mobile or user_id", "bet_amount", "win_amount", "wallet_before", "wallet_after", "game_round", "game_uid", "token"],
        }, status=200)

    data = _get_callback_data(request)
    logger.info("game_callback: received POST keys=%s", list(data.keys()) if data else [])

    def _get(key, default=""):
        val = data.get(key, default)
        return val if val is not None else default

    try:
        mobile = _get("mobile") or _get("user_id")
        callback_bet = Decimal(str(_get("bet_amount", "0")))
        callback_win = Decimal(str(_get("win_amount", "0")))
        game_uid = (_get("game_uid") or "").strip()
        game_round = (_get("game_round") or "").strip()
        token = _get("token") or ""
        wallet_before = Decimal(str(_get("wallet_before", "0")))
        wallet_after = Decimal(str(_get("wallet_after", "0")))
        change = Decimal(str(_get("change", "0")))
        timestamp = _get("timestamp") or timezone.now().isoformat()
    except Exception:
        logger.warning("game_callback: invalid parameters, data keys=%s", list(data.keys()) if data else [])
        return JsonResponse({"error": "Invalid parameters"}, status=400)

    # Resolve effective token: provider first, SuperSetting as fallback
    provider_token = ""
    if game_uid:
        from_game = Game.objects.filter(game_uid=game_uid).select_related("provider").first()
        if from_game and from_game.provider:
            provider_token = (from_game.provider.api_token or "").strip()

    super_settings = SuperSetting.get_settings()
    effective_token = provider_token or (
        (getattr(super_settings, "game_api_token", None) or "").strip()
        if super_settings else ""
    )

    if effective_token and (token or "").strip():
        if (token or "").strip() != effective_token:
            logger.warning("game_callback: token mismatch for mobile=%s", mobile)
            return JsonResponse({"error": "Invalid token"}, status=403)

    user = _get_user_by_mobile(mobile)
    if not user:
        logger.warning("game_callback: user not found for mobile=%s (try user_id or numeric id)", mobile)
        return JsonResponse({"error": "User not found"}, status=400)

    if not game_round:
        logger.warning("game_callback: game_round missing for user id=%s", user.pk)
        return JsonResponse({"error": "game_round required"}, status=400)

    game_uid = game_uid or "unknown"
    game = _get_or_create_game_and_provider(game_uid)
    is_bonus_wallet = _is_bonus_game_wallet(user)
    game_log_wallet = GameLogWallet.BONUS_BALANCE if is_bonus_wallet else GameLogWallet.MAIN_BALANCE
    transaction_wallet = TransactionWallet.BONUS_BALANCE if is_bonus_wallet else TransactionWallet.MAIN_BALANCE

    # API-doc aligned: use provider wallet_before/wallet_after as single source of truth
    result_amount = wallet_after - wallet_before

    if result_amount > 0:
        win = result_amount
        lose_amount_value = Decimal("0")
    elif result_amount < 0:
        win = Decimal("0")
        lose_amount_value = -result_amount
    else:
        win = Decimal("0")
        lose_amount_value = Decimal("0")

    if callback_bet > 0:
        bet = callback_bet
    elif result_amount < 0:
        bet = -result_amount
    else:
        bet = Decimal("0")

    result_win = win > 0
    log_type = GameLogType.WIN if result_win else GameLogType.LOSE
    net = result_amount

    existing = GameLog.objects.filter(user=user, round=game_round).first()
    # Provider two-callback pattern: 1st = bet/deduct, 2nd = result (win_amount) or round-end (bet=0, win=0, change=0).
    # When 2nd is round-end only, do not overwrite GameLog; when 2nd is result, preserve bet and before_balance from 1st.
    is_round_end_only = (
        callback_bet == 0 and callback_win == 0 and change == 0 and result_amount == 0
    )
    if existing and is_round_end_only:
        # Idempotent ack: keep existing GameLog, only sync balance to provider's wallet_after.
        _save_wallet_after(user, wallet_after)
        logger.info(
            "game_callback: round-end only (idempotent) user_id=%s game_round=%s wallet_after=%s",
            user.pk, game_round, wallet_after,
        )
        return JsonResponse({"status": "ok"}, status=200)

    if existing:
        # Second callback (result): provider often sends bet_amount=0; preserve first-callback bet and round-start balance.
        if callback_bet == 0 and existing.bet_amount > 0:
            bet = existing.bet_amount
            wallet_before = existing.before_balance
        existing.bet_amount = bet
        existing.win_amount = win
        existing.type = log_type
        existing.lose_amount = lose_amount_value
        existing.before_balance = wallet_before
        existing.after_balance = wallet_after
        existing.wallet = game_log_wallet
        existing.provider_raw_data = data
        existing.save(update_fields=["bet_amount", "win_amount", "type", "lose_amount", "before_balance", "after_balance", "wallet", "provider_raw_data", "updated_at"])
        game_log = existing
    else:
        game_log = GameLog.objects.create(
            user=user,
            game=game,
            provider=game.provider,
            wallet=game_log_wallet,
            type=log_type,
            round=game_round,
            bet_amount=bet,
            win_amount=win,
            lose_amount=lose_amount_value,
            before_balance=wallet_before,
            after_balance=wallet_after,
            provider_raw_data=data,
        )

    _save_wallet_after(user, wallet_after)

    master = getattr(user, "parent", None)
    if master and master.role == UserRole.MASTER:
        master.pl_balance = (master.pl_balance or Decimal("0")) - result_amount
        master.save(update_fields=["pl_balance"])

    # Create P/L transaction for every callback that has a net change (bet deduction or win/loss).
    # With two-callback pattern: 1st = bet (existing=False), 2nd = result (existing=True); both need a transaction.
    if net != 0:
        Transaction.objects.create(
            user=user,
            action_type=TransactionActionType.IN if net >= 0 else TransactionActionType.OUT,
            wallet=transaction_wallet,
            transaction_type=TransactionType.PL,
            amount=abs(net),
            status=TransactionStatus.SUCCESS,
            remarks=f"Game round {game_round}",
            game_log=game_log,
            balance_before=wallet_before,
            balance_after=wallet_after,
        )

    logger.info(
        "game_callback: ok user_id=%s game_round=%s bet=%s win=%s wallet_after=%s",
        user.pk, game_round, bet, win, wallet_after,
    )
    return JsonResponse({"status": "ok"}, status=200)
