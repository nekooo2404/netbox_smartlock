import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0001_initial"),
        ("netbox_smartlock", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="smartlock",
            name="rack",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlocks",
                to="dcim.rack",
                verbose_name="Rack",
            ),
        ),
        migrations.AddField(
            model_name="smartlock",
            name="rack_face",
            field=models.CharField(
                blank=True,
                choices=[("front", "Mặt trước"), ("rear", "Mặt sau")],
                max_length=10,
                verbose_name="Mặt rack",
            ),
        ),
    ]
