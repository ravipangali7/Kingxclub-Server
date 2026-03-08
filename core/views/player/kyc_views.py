from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import UserRole
from core.serializers import UserDetailSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kyc_status(request):
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    doc = request.user.kyc_document
    has_document = bool(doc and getattr(doc, 'name', None))
    return Response({
        'kyc_status': request.user.kyc_status,
        'kyc_reject_reason': request.user.kyc_reject_reason or '',
        'has_document': has_document,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def kyc_submit(request):
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    user = request.user
    if user.kyc_status == 'approved':
        return Response({'detail': 'KYC already approved.'}, status=status.HTTP_400_BAD_REQUEST)
    if user.kyc_status == 'pending' and user.kyc_document:
        return Response({'detail': 'KYC already submitted. Wait for review.'}, status=status.HTTP_400_BAD_REQUEST)
    doc = request.FILES.get('kyc_document') or request.data.get('kyc_document')
    if not doc:
        return Response({'detail': 'Document required.'}, status=status.HTTP_400_BAD_REQUEST)
    user.kyc_document = doc
    user.kyc_status = 'pending'
    user.save()
    return Response(UserDetailSerializer(user).data)
