"""
Public bonus: list active bonus rules (for bonus page).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models import BonusRule
from core.serializers import BonusRuleSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def bonus_rules_list(request):
    """GET active bonus rules."""
    qs = BonusRule.objects.filter(is_active=True)
    serializer = BonusRuleSerializer(qs, many=True)
    return Response(serializer.data)
