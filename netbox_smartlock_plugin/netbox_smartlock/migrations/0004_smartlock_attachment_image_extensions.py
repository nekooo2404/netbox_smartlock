import django.core.validators
import netbox_smartlock.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0003_smartlock_use_dcim_location_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="smartlock",
            name="attachment",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="smartlocks/attachments/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "gif", "webp", "bmp")
                    ),
                    netbox_smartlock.models.validate_file_size,
                ],
                verbose_name="File đính kèm",
            ),
        ),
    ]
