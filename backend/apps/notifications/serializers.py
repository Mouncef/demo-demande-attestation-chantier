from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "titre", "message", "payload", "lu", "lu_le", "created_at", "demande"]
        read_only_fields = fields
