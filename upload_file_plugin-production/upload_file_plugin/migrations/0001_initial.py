from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('file_name', models.CharField(max_length=255, blank=True)),
                ('file_url', models.URLField(max_length=500, blank=True)),
                ('object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('model_name', models.CharField(max_length=100, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)),
                ('session_key', models.CharField(max_length=40, blank=True, null=True)),
                ('file', models.FileField(upload_to='uploads/tmp/')),
            ],
        ),
    ]
