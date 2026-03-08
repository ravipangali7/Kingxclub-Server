"""
Notify player of approval events (deposit, withdrawal, bonus) via Message and real-time broadcast.
"""
from core.models import Message
from core.serializers import MessageSerializer
from core.channel_utils import broadcast_new_message_to_receiver


def notify_player_approval(user, processed_by, message_text):
    """
    Create a Message from processed_by to user and broadcast to the receiver's WebSocket group.
    Call only when user.role == UserRole.PLAYER so the player sees it in their Messages.
    """
    msg = Message.objects.create(
        sender=processed_by,
        receiver=user,
        message=message_text,
        is_read=False,
    )
    data = MessageSerializer(msg).data
    broadcast_new_message_to_receiver(user.id, data)
