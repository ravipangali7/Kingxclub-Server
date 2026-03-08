from django.db.models import Count
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
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    partner_id = request.query_params.get('partner_id')
    qs = Message.objects.filter(sender=request.user) | Message.objects.filter(receiver=request.user)
    if partner_id:
        try:
            pid = int(partner_id)
            qs = qs.filter(sender_id=pid) | qs.filter(receiver_id=pid)
            Message.objects.filter(receiver=request.user, sender_id=pid, is_read=False).update(is_read=True)
        except (TypeError, ValueError):
            pass
    qs = qs.select_related('sender', 'receiver').order_by('created_at').distinct()[:200]
    return Response(MessageSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_unread_count(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return Response({'unread_count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser, JSONParser])
def message_create(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    try:
        receiver_id = int(request.data.get('receiver'))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver_id != request.user.parent_id:
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
    """Return conversation partners for the player (users they have messages with) and unread count per partner."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    sender_ids = set(
        Message.objects.filter(receiver=request.user).values_list("sender_id", flat=True).distinct()
    )
    receiver_ids = set(
        Message.objects.filter(sender=request.user).values_list("receiver_id", flat=True).distinct()
    )
    partner_ids = sender_ids | receiver_ids
    if request.user.parent_id:
        partner_ids.add(request.user.parent_id)
    unread_map = dict(
        Message.objects.filter(receiver=request.user, is_read=False)
        .values("sender_id")
        .annotate(unread_count=Count("id"))
        .values_list("sender_id", "unread_count")
    )
    partners = []
    for uid in sorted(partner_ids):
        u = User.objects.filter(pk=uid).first()
        if u:
            partners.append({
                "id": u.id,
                "username": u.username,
                "name": u.name or u.username,
                "role": u.role,
                "unread_count": unread_map.get(u.id, 0),
            })
    return Response(partners)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Return unread messages for the player as notification items (sender, message preview, created_at) for the popup modal."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    qs = (
        Message.objects.filter(receiver=request.user, is_read=False)
        .select_related("sender")
        .order_by("-created_at")[:50]
    )
    notifications = []
    for msg in qs:
        preview = (msg.message or "").strip()
        if len(preview) > 100:
            preview = preview[:97] + "..."
        notifications.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_username": msg.sender.username if msg.sender else "",
            "sender_name": (msg.sender.name or msg.sender.username) if msg.sender else "",
            "message": preview,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })
    return Response(notifications)
