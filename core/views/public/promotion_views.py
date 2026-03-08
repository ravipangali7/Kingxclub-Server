"""
Public promotions: list active promotions (for promotions page).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models import Promotion
from core.serializers import PromotionSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def promotion_list(request):
    """GET active promotions, ordered by order then id."""
    qs = Promotion.objects.filter(is_active=True).order_by('order', 'id')
    serializer = PromotionSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)
