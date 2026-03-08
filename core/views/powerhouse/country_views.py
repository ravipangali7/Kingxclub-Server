"""Powerhouse: Country CRUD (country_code, currency_symbol for register/currency display)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import Country, UserRole
from core.serializers import CountrySerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def country_list_create(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    if request.method == 'GET':
        qs = Country.objects.all().order_by('name')
        return Response(CountrySerializer(qs, many=True).data)
    ser = CountrySerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def country_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = Country.objects.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(CountrySerializer(obj).data)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    ser = CountrySerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
