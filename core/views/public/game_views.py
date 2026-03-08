"""
Public games: GameCategory list, GameProvider list, Game list and detail (by category filter).
"""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import GameCategory, GameProvider, Game, ComingSoonEnrollment
from core.serializers import (
    GameCategorySerializer,
    GameProviderSerializer,
    GameListSerializer,
    GameDetailSerializer,
    ComingSoonGameSerializer,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """GET game categories (active)."""
    qs = GameCategory.objects.filter(is_active=True)
    serializer = GameCategorySerializer(qs, many=True)
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([AllowAny])
def provider_list(request):
    """GET game providers (active)."""
    qs = GameProvider.objects.filter(is_active=True)
    serializer = GameProviderSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def provider_detail(request, pk):
    """GET single provider by id (active only). Returns provider data, games_count, and categories with games."""
    obj = GameProvider.objects.filter(pk=pk, is_active=True).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    provider_data = GameProviderSerializer(obj).data
    games_count = Game.objects.filter(provider_id=pk, is_active=True, is_coming_soon=False).count()
    categories_qs = (
        Game.objects.filter(provider_id=pk, is_active=True, is_coming_soon=False)
        .values_list('category_id', 'category__name', 'category__icon', 'category__svg')
        .distinct()
    )
    from django.conf import settings
    def _media_url(field):
        if not field:
            return None
        name = str(field)
        if name.startswith(('http://', 'https://', 'data:', '<svg')):
            return name
        return request.build_absolute_uri(settings.MEDIA_URL + name)
    categories = [
        {'id': cid, 'name': cname or '', 'icon': _media_url(cicon) or _media_url(csvg)}
        for cid, cname, cicon, csvg in categories_qs
    ]
    return Response({
        **provider_data,
        'games_count': games_count,
        'categories': categories,
    })


def _paginate_queryset(qs, request, page_size=24):
    """Paginate queryset; return (page_queryset, count, next_page, prev_page)."""
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = max(1, min(100, int(request.query_params.get('page_size', page_size))))
    except (ValueError, TypeError):
        page_size = 24
    count = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    page_qs = qs[start:end]
    next_page = page + 1 if end < count else None
    previous_page = page - 1 if page > 1 else None
    return page_qs, count, next_page, previous_page


@api_view(['GET'])
@permission_classes([AllowAny])
def game_list(request):
    """GET games (active). Optional query: category_id, provider_id, search, page, page_size, ids."""
    # If specific IDs are requested, return only those in the given order (no pagination).
    ids_param = request.query_params.get('ids')
    if ids_param:
        id_list = [int(i) for i in ids_param.split(',') if i.strip().isdigit()]
        games_by_id = {
            g.id: g
            for g in Game.objects.filter(is_active=True, is_coming_soon=False, id__in=id_list).select_related('category', 'provider')
        }
        ordered = [games_by_id[i] for i in id_list if i in games_by_id]
        serializer = GameListSerializer(ordered, many=True)
        return Response({'count': len(ordered), 'next': None, 'previous': None, 'results': serializer.data})

    qs = Game.objects.filter(is_active=True, is_coming_soon=False).select_related('category', 'provider').order_by('id')
    category_id = request.query_params.get('category_id') or request.query_params.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)
    provider_id = request.query_params.get('provider_id') or request.query_params.get('provider')
    if provider_id:
        qs = qs.filter(provider_id=provider_id)
    search = (request.query_params.get('search') or '').strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(game_uid__icontains=search)
            | Q(provider__name__icontains=search)
            | Q(provider__code__icontains=search)
        )
    is_top_game = request.query_params.get('is_top_game')
    if is_top_game is not None and str(is_top_game).lower() in ('true', '1', 'yes'):
        qs = qs.filter(is_top_game=True)
    is_popular_game = request.query_params.get('is_popular_game')
    if is_popular_game is not None and str(is_popular_game).lower() in ('true', '1', 'yes'):
        qs = qs.filter(is_popular_game=True)
    page_qs, count, next_page, previous_page = _paginate_queryset(qs, request, page_size=24)
    serializer = GameListSerializer(page_qs, many=True)
    base = request.build_absolute_uri(request.path)
    next_url = None
    prev_url = None
    if next_page is not None:
        p = request.GET.copy()
        p['page'] = next_page
        next_url = f"{base}?{p.urlencode()}"
    if previous_page is not None:
        p = request.GET.copy()
        p['page'] = previous_page
        prev_url = f"{base}?{p.urlencode()}"
    return Response({
        'count': count,
        'next': next_url,
        'previous': prev_url,
        'results': serializer.data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def coming_soon_list(request):
    """GET games marked as coming soon (active + is_coming_soon=True)."""
    qs = Game.objects.filter(is_active=True, is_coming_soon=True).select_related('category', 'provider').order_by('id')
    serializer = ComingSoonGameSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def coming_soon_enroll(request):
    """POST: enroll current user for a coming-soon game (game_id in body). Idempotent."""
    game_id = request.data.get('game_id')
    if game_id is None:
        return Response({'detail': 'game_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        game_id = int(game_id)
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid game_id.'}, status=status.HTTP_400_BAD_REQUEST)
    game = Game.objects.filter(pk=game_id, is_active=True, is_coming_soon=True).first()
    if not game:
        return Response({'detail': 'Game not found or not coming soon.'}, status=status.HTTP_404_NOT_FOUND)
    _, created = ComingSoonEnrollment.objects.get_or_create(
        game=game,
        user=request.user,
        defaults={},
    )
    return Response({'detail': 'Enrolled.' if created else 'Already enrolled.', 'enrolled': created}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def game_detail(request, pk):
    """GET single game by id."""
    obj = Game.objects.filter(pk=pk, is_active=True).select_related('category', 'provider').first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = GameDetailSerializer(obj)
    return Response(serializer.data)
