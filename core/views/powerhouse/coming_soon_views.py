"""Powerhouse: Coming Soon CRUD."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import ComingSoon, UserRole
from core.serializers import ComingSoonSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def coming_soon_list_create(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    if request.method == 'GET':
        qs = ComingSoon.objects.all().order_by('coming_date', 'id')
        return Response(ComingSoonSerializer(qs, many=True, context={'request': request}).data)
    ser = ComingSoonSerializer(data=request.data, context={'request': request})
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def coming_soon_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = ComingSoon.objects.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(ComingSoonSerializer(obj, context={'request': request}).data)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    ser = ComingSoonSerializer(
        obj, data=request.data, partial=(request.method == 'PATCH'), context={'request': request}
    )
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
