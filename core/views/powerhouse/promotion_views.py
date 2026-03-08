"""Powerhouse: Promotion CRUD."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import Promotion, UserRole
from core.serializers import PromotionSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def promotion_list_create(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    if request.method == 'GET':
        qs = Promotion.objects.all().order_by('order', 'id')
        return Response(PromotionSerializer(qs, many=True, context={'request': request}).data)
    ser = PromotionSerializer(data=request.data, context={'request': request})
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def promotion_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = Promotion.objects.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(PromotionSerializer(obj, context={'request': request}).data)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    ser = PromotionSerializer(
        obj, data=request.data, partial=(request.method == 'PATCH'), context={'request': request}
    )
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
