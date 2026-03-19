import json
import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from core.permissions import require_role
from core.models import SiteSetting, UserRole
from core.serializers import SiteSettingSerializer

# Main color keys only: dark/light feel + brand. Must match frontend SITE_THEME_KEYS.
ALLOWED_SITE_THEME_KEYS = frozenset({
    'background', 'foreground', 'card', 'muted', 'muted_foreground',
    'border', 'primary', 'primary_foreground', 'accent', 'accent_foreground',
    'ring', 'gold',
})


def _sanitize_site_theme_json(value):
    """Return a dict with only allowed theme keys; values must be strings.
    Values may be hex, rgb, hsl, cmyk, or hsv; frontend converts to HSL when applying."""
    parsed = _parse_json_field(value, {})
    if not isinstance(parsed, dict):
        return {}
    return {
        k: str(v).strip() for k, v in parsed.items()
        if k in ALLOWED_SITE_THEME_KEYS and v is not None and str(v).strip()
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def site_setting_get(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SiteSetting.objects.first()
    return Response(SiteSettingSerializer(obj).data if obj else None)


def _parse_promo_banners(value):
    if value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


def _parse_json_field(value, default=None):
    if default is None:
        default = []
    if value is None or value == '':
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _parse_positive_int(value):
    if value is None or value == '':
        return None
    try:
        n = int(value)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def _parse_decimal(value):
    if value is None or value == '':
        return None
    try:
        from decimal import Decimal
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


def _decimal_or_zero(value):
    from decimal import Decimal
    parsed = _parse_decimal(value)
    return parsed if parsed is not None else Decimal('0')


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def site_setting_update(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SiteSetting.objects.first() or SiteSetting()
    data = request.data

    # Accept multipart/form-data for logo and favicon file upload
    if request.FILES.get('logo') or request.FILES.get('favicon'):
        data = {
            'name': request.data.get('name') or '',
            'phones': [x for x in [request.data.get('phone1'), request.data.get('phone2')] if x],
            'emails': [x for x in [request.data.get('email1')] if x],
            'whatsapp_number': request.data.get('whatsapp_number') or '',
            'hero_title': request.data.get('hero_title') or '',
            'hero_subtitle': request.data.get('hero_subtitle') or '',
            'scrolling_text': request.data.get('scrolling_text') if request.data.get('scrolling_text') is not None else '',
            'footer_description': request.data.get('footer_description') or '',
            'promo_banners': _parse_promo_banners(request.data.get('promo_banners')),
            'active_players': _parse_positive_int(request.data.get('active_players')) or 0,
            'games_available': _parse_positive_int(request.data.get('games_available')) or 0,
            'total_winnings': _decimal_or_zero(request.data.get('total_winnings')),
            'instant_payouts': _parse_positive_int(request.data.get('instant_payouts')) or 0,
            'home_stats': _parse_json_field(request.data.get('home_stats'), []),
            'biggest_wins': _parse_json_field(request.data.get('biggest_wins'), []),
            'site_categories_json': _parse_json_field(request.data.get('site_categories_json'), {}),
            'site_top_games_json': _parse_json_field(request.data.get('site_top_games_json'), {}),
            'site_providers_json': _parse_json_field(request.data.get('site_providers_json'), {}),
            'site_categories_game_json': _parse_json_field(request.data.get('site_categories_game_json'), {}),
            'site_popular_games_json': _parse_json_field(request.data.get('site_popular_games_json'), {}),
            'site_refer_bonus_json': _parse_json_field(request.data.get('site_refer_bonus_json'), {}),
            'site_payments_accepted_json': _parse_json_field(request.data.get('site_payments_accepted_json'), {}),
            'site_footer_json': _parse_json_field(request.data.get('site_footer_json'), {}),
            'site_welcome_deposit_json': _parse_json_field(request.data.get('site_welcome_deposit_json'), {}),
            'site_theme_json': _sanitize_site_theme_json(request.data.get('site_theme_json')),
        }
        if request.FILES.get('logo'):
            data['logo'] = request.FILES.get('logo')
        if request.FILES.get('favicon'):
            data['favicon'] = request.FILES.get('favicon')
    else:
        if 'site_theme_json' in data:
            data = dict(data)
            data['site_theme_json'] = _sanitize_site_theme_json(data.get('site_theme_json'))

    ser = SiteSettingSerializer(obj, data=data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_site_media(request):
    """Upload an image for site section icons etc. Returns { url: "<relative path>" }."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    file = request.FILES.get('file') or request.FILES.get('image')
    if not file:
        return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
    name = getattr(file, 'name', '') or 'image'
    ext = ''
    if '.' in name:
        ext = '.' + name.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = '.png'
    path = f"site/sections/{uuid.uuid4().hex}{ext}"
    saved_path = default_storage.save(path, file)
    return Response({'url': saved_path})
