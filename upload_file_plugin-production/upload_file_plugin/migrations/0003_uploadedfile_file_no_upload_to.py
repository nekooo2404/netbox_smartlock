from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("upload_file_plugin", "0002_deleteColumnFile_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="UploadedFile",
            name="file",
            field=models.FileField(max_length=1000),
        ),
    ]
