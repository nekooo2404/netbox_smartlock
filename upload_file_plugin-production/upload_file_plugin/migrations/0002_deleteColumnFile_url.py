from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('upload_file_plugin', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='UploadedFile',
            name='file_url',
        ),
        migrations.AlterField(
            model_name='UploadedFile',
            name='file',
            field=models.FileField(upload_to='uploads/tmp/', max_length=1000),
        ),
    ]