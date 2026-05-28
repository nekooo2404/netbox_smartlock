from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class UploadedFile(models.Model):
    id = models.AutoField(primary_key=True)
    file = models.FileField(max_length=1000)
    file_name = models.CharField(max_length=255, blank=True)
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.name
        if self.content_type and not self.model_name:
            self.model_name = self.content_type.model
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file_name or self.file.name
