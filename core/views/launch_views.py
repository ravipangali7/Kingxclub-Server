"""Game launch: build provider URL and redirect authenticated user."""
from django.conf import settings as django_settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import SuperSetting, UserRole, Game
from core.game_api_client import launch_game, build_launch_url


def _normalize_launch_base(launch_base: str) -> str:
    """AllAPI expects launch_game1_js; launch_game_js returns 'Wrong or missing Parameter'."""
    base_rstrip = launch_base.rstrip("/")
    if base_rstrip.endswith("/launch_game_js"):
        return base_rstrip.replace("/launch_game_js", "/launch_game1_js")
    if base_rstrip in ("https://allapi.online", "http://allapi.online"):
        return base_rstrip + "/launch_game1_js"
    return launch_base.rstrip("/")


def _wallet_amount_for_launch(user, min_bet):
    """Send only main_balance when main > 0; only bonus_balance when main is 0 and bonus >= min_bet. Never main + bonus."""
    main = float(user.main_balance or 0)
    bonus = float(user.bonus_balance or 0)
    min_bet_f = float(min_bet) if min_bet is not None else 0
    if main > 0:
        return main
    if bonus >= min_bet_f:
        return bonus
    return 0


def _launch_game_common(request):
    """Shared logic: validate player, get game_uid, call provider, return (location_url or None, error_response or None)."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return None, err
    game_uid = request.GET.get("game_uid") or request.query_params.get("game_uid")
    if not game_uid or not game_uid.strip():
        return None, Response(
            {"detail": "game_uid is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    game_uid = game_uid.strip()
    settings = SuperSetting.get_settings()
    if not settings or not settings.game_api_url or not settings.game_api_secret or not settings.game_api_token:
        return None, Response(
            {"detail": "Game API not configured (game_api_url, secret, token)."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    user = request.user
    game = Game.objects.filter(game_uid=game_uid).first()
    min_bet = game.min_bet if game else 0
    wallet_amount = _wallet_amount_for_launch(user, min_bet)
    launch_base = (getattr(settings, "game_api_launch_url", None) or "").strip() or settings.game_api_url
    launch_base = _normalize_launch_base(launch_base)
    user_id = str(user.pk)
    domain_url = (settings.game_api_domain_url or "").strip() or None
    try:
        r = launch_game(
            base_url=launch_base.rstrip("/"),
            secret_key=settings.game_api_secret,
            token=settings.game_api_token,
            user_id=user_id,
            wallet_amount=wallet_amount,
            game_uid=game_uid,
            domain_url=domain_url,
            allow_redirects=False,
        )
    except Exception as e:
        return None, Response(
            {"detail": f"Launch failed: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
        return r.headers["Location"], None
    return None, Response(
        {"detail": "Provider did not redirect.", "status": r.status_code, "body": r.text[:500]},
        status=status.HTTP_502_BAD_GATEWAY,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def launch_game_redirect(request):
    """
    GET ?game_uid=... - Redirect to provider launch URL.
    Requires authenticated player. Uses SuperSetting for base_url, secret, token, domain_url.
    """
    location_url, err = _launch_game_common(request)
    if err is not None:
        return err
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(location_url)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def launch_game_url(request):
    """
    GET ?game_uid=... - Return launch URL in JSON for React to open in new tab.
    Requires authenticated player. Returns {"url": "..."} on success.
    """
    location_url, err = _launch_game_common(request)
    if err is not None:
        return err
    return Response({"url": location_url})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def launch_game_by_id(request, game_id):
    """
    GET /api/player/games/<game_id>/launch/
    Returns {"launch_url": "https://..."}. Requires authenticated player.
    Validates game (active, has game_uid), provider (active, has endpoint or global config).
    """
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err

    game = Game.objects.select_related("provider").filter(pk=game_id).first()
    if not game:
        return Response({"error": "Game not found"}, status=status.HTTP_404_NOT_FOUND)
    if not game.is_active:
        return Response({"error": "Game is not available"}, status=status.HTTP_400_BAD_REQUEST)
    if not (game.game_uid and game.game_uid.strip()):
        return Response({"error": "Game has no provider identifier"}, status=status.HTTP_400_BAD_REQUEST)
    game_uid = game.game_uid.strip()

    provider = game.provider
    super_settings = SuperSetting.get_settings()

    if not provider.is_active:
        return Response({"error": "Game provider is not available"}, status=status.HTTP_400_BAD_REQUEST)

    # Resolve launch URL: provider api_endpoint, or fallback to SuperSetting game_api_launch_url / game_api_url
    launch_base = (provider.api_endpoint or "").strip()
    if not launch_base and super_settings:
        launch_base = (getattr(super_settings, "game_api_launch_url", None) or "").strip() or (super_settings.game_api_url or "").strip()
    if not launch_base:
        return Response({"error": "Game provider is not available"}, status=status.HTTP_400_BAD_REQUEST)
    launch_base = _normalize_launch_base(launch_base)

    # Resolve secret/token: provider values, or fallback to SuperSetting (super game) when provider fields are blank
    api_secret = (provider.api_secret or "").strip()
    if not api_secret and super_settings:
        api_secret = (getattr(super_settings, "game_api_secret", None) or "").strip()
    if not api_secret:
        return Response(
            {"error": "Provider API secret is not set. Configure it in the provider form or in SuperSetting (super game)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    api_token = (provider.api_token or "").strip()
    if not api_token and super_settings:
        api_token = (getattr(super_settings, "game_api_token", None) or "").strip()
    if not api_token:
        return Response(
            {"error": "Provider API token is not set. Configure it in the provider form or in SuperSetting (super game)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    domain_url = None
    if super_settings and (super_settings.game_api_domain_url or "").strip():
        domain_url = (super_settings.game_api_domain_url or "").strip()
    if not domain_url:
        domain_url = getattr(django_settings, "SITE_DOMAIN", None) or ""
    if domain_url:
        domain_url = domain_url.strip()
    if not domain_url and request:
        domain_url = request.build_absolute_uri("/").rstrip("/") or None

    callback_url = None
    if super_settings and (super_settings.game_api_callback_url or "").strip():
        callback_url = (super_settings.game_api_callback_url or "").strip()
    if not callback_url and request:
        callback_url = request.build_absolute_uri("/api/callback/").rstrip("/") or None

    user = request.user
    wallet_amount = _wallet_amount_for_launch(user, game.min_bet)
    user_id = str(user.pk)

    try:
        launch_url = build_launch_url(
            base_url=launch_base,
            secret_key=api_secret,
            token=api_token,
            user_id=user_id,
            wallet_amount=wallet_amount,
            game_uid=game_uid,
            domain_url=domain_url or None,
            callback_url=callback_url or None,
        )
    except Exception as e:
        return Response(
            {"error": "Failed to build launch URL", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"launch_url": launch_url}, status=status.HTTP_200_OK)
