from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("netbox_smartlock", "0010_access_request_admin_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="accessrequest",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="access_requests",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Created By",
            ),
        ),
    ]
