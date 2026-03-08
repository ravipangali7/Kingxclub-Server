"""Powerhouse: Direct import of providers/games. Backend exposes game API URL only; React calls game API from browser."""
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import SuperSetting, GameProvider, GameCategory, Game, UserRole


def _get_base_url():
    settings = SuperSetting.get_settings()
    if not settings or not settings.game_api_url or not settings.game_api_url.strip():
        return None
    return settings.game_api_url.strip()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_game_api_url(request):
    """GET game API base URL for frontend to call getProvider/providerGame from browser. Powerhouse only."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    base_url = _get_base_url()
    if not base_url:
        return Response(
            {"detail": "Game API URL not set. Configure it in Super Settings.", "game_api_url": ""},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({"game_api_url": base_url})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_games_create(request):
    """POST import selected games: get_or_create provider/categories, create games (skip existing). Powerhouse only."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    data = request.data or {}
    provider_code = (data.get("provider_code") or "").strip()
    provider_name = (data.get("provider_name") or "").strip() or provider_code
    games = data.get("games")
    if not provider_code:
        return Response(
            {"detail": "provider_code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(games, list):
        return Response(
            {"detail": "games must be a list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider, provider_created = GameProvider.objects.get_or_create(
        code=provider_code,
        defaults={"name": provider_name, "is_active": True},
    )
    if not provider_created and provider.name != provider_name:
        provider.name = provider_name
        provider.save(update_fields=["name"])

    categories_created = 0
    games_created = 0
    games_skipped = 0
    default_category_name = "Other"

    for g in games:
        if not isinstance(g, dict):
            continue
        game_uid = (g.get("game_uid") or g.get("game_code") or "").strip()
        if not game_uid:
            continue
        game_name = (g.get("game_name") or "").strip() or game_uid
        game_type = (g.get("game_type") or "").strip() or default_category_name
        game_image = (g.get("game_image") or "").strip() or None
        cat_name = game_type[:255] if game_type else default_category_name

        cat, cat_created = GameCategory.objects.get_or_create(
            name=cat_name,
            defaults={"is_active": True},
        )
        if cat_created:
            categories_created += 1

        _, created = Game.objects.get_or_create(
            provider=provider,
            game_uid=game_uid,
            defaults={
                "name": game_name[:255],
                "category": cat,
                "image_url": game_image,
                "is_active": True,
                "min_bet": Decimal("0"),
                "max_bet": Decimal("0"),
            },
        )
        if created:
            games_created += 1
        else:
            games_skipped += 1

    return Response({
        "provider_created": provider_created,
        "categories_created": categories_created,
        "games_created": games_created,
        "games_skipped": games_skipped,
    })
