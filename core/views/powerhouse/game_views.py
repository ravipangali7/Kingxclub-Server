"""Powerhouse: Game, Category, Provider CRUD."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import Game, GameCategory, GameProvider, UserRole
from core.serializers import (
    GameListSerializer,
    GameDetailSerializer,
    GameCategorySerializer,
    GameProviderSerializer,
)

_BOOL_GAME_FIELDS = (
    'is_active', 'is_top_game', 'is_popular_game', 'is_lobby',
)


def _coerce_multipart_booleans(data):
    """
    Return a mutable copy of request.data with boolean string values ('true'/'false'/etc.)
    converted to actual Python booleans. Required when form-data (multipart) is used
    because DRF's BooleanField does not accept the string 'true'/'false' by default
    in multipart context.
    """
    mutable = data.copy()
    for field in _BOOL_GAME_FIELDS:
        if field in mutable:
            val = mutable[field]
            if isinstance(val, str):
                mutable[field] = val.lower() in ('true', '1', 'yes')
    return mutable


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def category_list_create(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    if request.method == 'GET':
        qs = GameCategory.objects.all().order_by('name')
        return Response(GameCategorySerializer(qs, many=True).data)
    ser = GameCategorySerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def category_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = GameCategory.objects.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(GameCategorySerializer(obj).data)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    ser = GameCategorySerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def provider_list_create(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    if request.method == 'GET':
        qs = GameProvider.objects.all().order_by('name')
        return Response(GameProviderSerializer(qs, many=True).data)
    ser = GameProviderSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def provider_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = GameProvider.objects.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(GameProviderSerializer(obj).data)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    ser = GameProviderSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def game_list_create(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    if request.method == 'GET':
        qs = Game.objects.all().select_related('category', 'provider').order_by('name')
        provider_ids_param = request.query_params.get('provider_ids')
        if provider_ids_param:
            try:
                ids = [int(i.strip()) for i in provider_ids_param.split(',') if i.strip().isdigit()]
                if ids:
                    qs = qs.filter(provider_id__in=ids)
            except (ValueError, TypeError):
                pass
        else:
            provider_id_param = request.query_params.get('provider_id') or request.query_params.get('provider')
            if provider_id_param:
                try:
                    pid = int(provider_id_param)
                    qs = qs.filter(provider_id=pid)
                except (ValueError, TypeError):
                    pass
        return Response(GameListSerializer(qs, many=True).data)
    data = _coerce_multipart_booleans(request.data)
    ser = GameDetailSerializer(data=data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def game_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = Game.objects.filter(pk=pk).select_related('category', 'provider').first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(GameDetailSerializer(obj).data)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    data = _coerce_multipart_booleans(request.data)
    ser = GameDetailSerializer(obj, data=data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
