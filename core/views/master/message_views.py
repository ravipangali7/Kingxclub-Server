from django.db.models import Q, Count
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import Message, User, UserRole
from core.serializers import MessageSerializer, MessageCreateSerializer
from core.channel_utils import broadcast_new_message_to_receiver


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    partner_id = request.query_params.get('partner_id')
    qs = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver')
    if partner_id:
        try:
            pid = int(partner_id)
            qs = qs.filter(Q(sender_id=pid) | Q(receiver_id=pid))
        except (TypeError, ValueError):
            pass
    qs = qs.order_by('created_at')[:200]
    if partner_id:
        try:
            pid = int(partner_id)
            Message.objects.filter(receiver=request.user, sender_id=pid, is_read=False).update(is_read=True)
        except (TypeError, ValueError):
            pass
    return Response(MessageSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_unread_count(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return Response({'unread_count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser, JSONParser])
def message_create(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    receiver_id = request.data.get('receiver')
    receiver = User.objects.filter(pk=receiver_id).first()
    if not receiver:
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver.role == UserRole.PLAYER and receiver.parent_id != request.user.id:
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver.role == UserRole.SUPER and receiver.id != request.user.parent_id:
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    data = {k: v for k, v in request.data.items()}
    data['receiver'] = receiver_id
    if 'file' in request.FILES:
        data['file'] = request.FILES['file']
    if 'image' in request.FILES:
        data['image'] = request.FILES['image']
    ser = MessageCreateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    msg = ser.save(sender=request.user)
    data = MessageSerializer(msg).data
    broadcast_new_message_to_receiver(msg.receiver_id, data)
    broadcast_new_message_to_receiver(msg.sender_id, data)
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_contacts(request):
    """Return allowed conversation partners: parent (Super) + all players under this master."""
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    unread_map = dict(
        Message.objects.filter(receiver=request.user, is_read=False)
        .values("sender_id")
        .annotate(unread_count=Count("id"))
        .values_list("sender_id", "unread_count")
    )
    partners = []
    if request.user.parent_id:
        parent = User.objects.filter(pk=request.user.parent_id).first()
        if parent:
            partners.append({
                "id": parent.id,
                "username": parent.username,
                "name": parent.name or parent.username,
                "role": parent.role,
                "unread_count": unread_map.get(parent.id, 0),
            })
    children = User.objects.filter(parent=request.user, role=UserRole.PLAYER).order_by("username")
    for u in children:
        partners.append({
            "id": u.id,
            "username": u.username,
            "name": u.name or u.username,
            "role": u.role,
            "unread_count": unread_map.get(u.id, 0),
        })
    return Response(partners)
