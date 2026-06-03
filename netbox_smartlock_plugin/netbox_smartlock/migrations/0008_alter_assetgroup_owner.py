import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0007_remove_smartlock_location_catalogs"),
        ("users", "0015_owner"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetgroup",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="users.owner",
            ),
        ),
    ]
