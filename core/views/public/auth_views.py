"""
Public auth: login, register, Google OAuth. Authenticated: me (current user + balances).
"""
import re
import requests
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from core.models import User, UserRole, SignupSession, SuperSetting, SiteSetting, ActivityAction
from core.serializers import (
    LoginSerializer,
    RegisterSerializer,
    MeSerializer,
)
from core.services.bonus_service import apply_referral_bonus
from core.services.activity_log_service import create_activity_log
from core.views.public.signup_views import normalize_phone
from core.channel_utils import broadcast_session_revoked

# Username for Google signup: alphanumeric and underscore only, 3–30 chars
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,30}$')


def get_default_master():
    """Return the default master user for new signups (no referral)."""
    settings = SuperSetting.get_settings()
    if settings and settings.default_master_id:
        return settings.default_master
    return User.objects.filter(role=UserRole.MASTER).first()


def _get_google_auth_config():
    site = SiteSetting.objects.first()
    if not site:
        return {'enabled': False, 'client_id': '', 'client_secret': '', 'redirect_uri': ''}
    return {
        'enabled': bool(getattr(site, 'google_auth_enabled', False)),
        'client_id': (getattr(site, 'google_client_id', '') or '').strip(),
        'client_secret': (getattr(site, 'google_client_secret', '') or '').strip(),
        'redirect_uri': (getattr(site, 'google_redirect_uri', '') or '').strip(),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """POST { username, password } -> { token, user }."""
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = authenticate(
        request,
        username=ser.validated_data['username'],
        password=ser.validated_data['password'],
    )
    if not user:
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_active:
        return Response(
            {'detail': 'User account is disabled.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    create_activity_log(user, ActivityAction.LOGIN, request=request)
    country_code = (ser.validated_data.get('country_code') or '').strip()
    if country_code in ('977', '91'):
        user.country_code = country_code
        user.save(update_fields=['country_code'])
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    broadcast_session_revoked(user.id, token.key)
    serializer = MeSerializer(user)
    return Response({
        'token': token.key,
        'user': serializer.data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST { signup_token, phone, name, password, referral_code? }. Creates user after OTP verification."""
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data.copy()
    signup_token = (data.get('signup_token') or '').strip()
    phone_raw = (data.get('phone') or '').strip()
    normalized_phone = normalize_phone(phone_raw)
    if not normalized_phone or len(normalized_phone) < 10:
        return Response({'detail': 'Invalid phone number.'}, status=status.HTTP_400_BAD_REQUEST)

    session = (
        SignupSession.objects.filter(token=signup_token, phone=normalized_phone)
        .filter(expires_at__gt=timezone.now())
        .first()
    )
    if not session:
        return Response({'detail': 'Invalid or expired signup token.'}, status=status.HTTP_400_BAD_REQUEST)

    referral_code = (data.pop('referral_code', None) or '').strip()
    parent = None
    referred_by = None
    if referral_code:
        referrer = User.objects.filter(username=referral_code).first()
        if referrer and referrer.role == UserRole.PLAYER and referrer.parent_id:
            parent = referrer.parent
            referred_by = referrer
    if parent is None:
        parent = get_default_master()
    if not parent:
        return Response({'detail': 'No default master configured. Contact support.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    username = normalized_phone
    if User.objects.filter(username=username).exists():
        username = f"user_{normalized_phone}"
    name = (data.get('name') or '').strip() or username
    password = data['password']
    country_code = (data.get('country_code') or '').strip()
    if country_code not in ('977', '91'):
        country_code = ''

    user = User(
        username=username,
        role=UserRole.PLAYER,
        name=name,
        phone=normalized_phone,
        email='',
        whatsapp_number='',
        country_code=country_code,
        parent=parent,
        referred_by=referred_by,
    )
    user.set_password(password)
    user.save()

    if user.referred_by_id:
        apply_referral_bonus(user.referred_by, user)

    SignupSession.objects.filter(token=signup_token).delete()
    token = Token.objects.create(user=user)
    serializer = MeSerializer(user)
    return Response({
        'token': token.key,
        'user': serializer.data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """GET current user and header balances."""
    u = User.objects.select_related('parent').get(pk=request.user.pk)
    serializer = MeSerializer(u)
    return Response(serializer.data)


def _verify_google_id_token(id_token):
    """
    Verify Google id_token via tokeninfo endpoint. Returns payload dict with sub, email, name
    or None if invalid. Validates audience if Google client_id is set.
    """
    if not id_token or not id_token.strip():
        return None
    client_id = _get_google_auth_config()['client_id']
    try:
        r = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': id_token.strip()},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        sub = data.get('sub')
        if not sub:
            return None
        if client_id and data.get('aud') != client_id:
            return None
        email = (data.get('email') or '').strip()
        name = (data.get('name') or '').strip()
        if not name and (data.get('given_name') or data.get('family_name')):
            name = ' '.join(filter(None, [data.get('given_name', '').strip(), data.get('family_name', '').strip()]))
        return {'sub': sub, 'email': email, 'name': name}
    except Exception:
        return None


@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """
    POST { id_token }.
    If user exists for this Google account -> { token, user }.
    If new -> { needs_username: true, email, name } (no user created yet).
    """
    google_cfg = _get_google_auth_config()
    if not google_cfg['enabled'] or not google_cfg['client_id']:
        return Response(
            {'detail': 'Google login is not configured.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    id_token = (request.data.get('id_token') or '').strip()
    if not id_token:
        return Response({'detail': 'id_token is required.'}, status=status.HTTP_400_BAD_REQUEST)
    payload = _verify_google_id_token(id_token)
    if not payload:
        return Response(
            {'detail': 'Invalid or expired Google token. Please try again.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = User.objects.filter(google_id=payload['sub']).first()
    if user:
        if not user.is_active:
            return Response(
                {'detail': 'User account is disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        create_activity_log(user, ActivityAction.LOGIN, request=request)
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        broadcast_session_revoked(user.id, token.key)
        serializer = MeSerializer(user)
        return Response({'token': token.key, 'user': serializer.data})
    return Response({
        'needs_username': True,
        'email': payload['email'],
        'name': payload['name'],
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_complete(request):
    """
    POST { id_token, username, password }. Creates user for new Google signup after username and password are provided.
    Returns { token, user }.
    """
    google_cfg = _get_google_auth_config()
    if not google_cfg['enabled'] or not google_cfg['client_id']:
        return Response(
            {'detail': 'Google login is not configured.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    id_token = (request.data.get('id_token') or '').strip()
    username = (request.data.get('username') or '').strip()
    password = (request.data.get('password') or '').strip()
    if not id_token:
        return Response({'detail': 'id_token is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not username:
        return Response({'detail': 'username is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not password:
        return Response({'detail': 'password is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 6:
        return Response(
            {'detail': 'Password must be at least 6 characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not USERNAME_REGEX.match(username):
        return Response(
            {'detail': 'Username must be 3–30 characters, letters, numbers and underscores only.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if User.objects.filter(username__iexact=username).exists():
        return Response({'detail': 'This username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
    payload = _verify_google_id_token(id_token)
    if not payload:
        return Response(
            {'detail': 'Invalid or expired Google token. Please try again.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if User.objects.filter(google_id=payload['sub']).exists():
        return Response(
            {'detail': 'An account for this Google account already exists. Please log in.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    parent = get_default_master()
    if not parent:
        return Response(
            {'detail': 'No default master configured. Contact support.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    name = (payload.get('name') or '').strip() or username
    email = (payload.get('email') or '').strip()
    user = User(
        username=username,
        role=UserRole.PLAYER,
        name=name,
        email=email,
        phone='',
        whatsapp_number='',
        google_id=payload['sub'],
        parent=parent,
        referred_by=None,
    )
    user.set_password(password)
    user.save()
    token = Token.objects.create(user=user)
    serializer = MeSerializer(user)
    return Response({
        'token': token.key,
        'user': serializer.data,
    }, status=status.HTTP_201_CREATED)
