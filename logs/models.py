from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder


class AuditLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    username = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    path = models.CharField(max_length=1024, blank=True)
    method = models.CharField(max_length=10, blank=True)
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=200, blank=True)
    resource_id = models.CharField(max_length=255, blank=True)
    resource_name = models.CharField(max_length=255, blank=True)
    detail = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    metadata = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.action} {self.resource_type}#{self.resource_id} by {self.username or 'anon'}"
