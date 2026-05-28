#!/bin/bash
set -e

echo "Checking NetBox plugin bootstrap..."

docker compose run --rm --entrypoint /bin/sh netbox -lc '
  cd /opt/netbox/netbox &&
  /opt/netbox/venv/bin/python - <<'"'"'PY'"'"'
import importlib
import traceback

checks = [
    "netbox_smartlock.urls",
    "netbox_smartlock.views",
    "netbox_smartlock.forms",
    "netbox_smartlock.contracts",
    "netbox_smartlock.exports",
    "netbox_smartlock.services",
    "upload_file_plugin.integration",
    "upload_file_plugin.services",
]

for module_name in checks:
    try:
        module = importlib.import_module(module_name)
        print(f"OK  {module_name}")
        if module_name.endswith(".urls"):
            urlpatterns = getattr(module, "urlpatterns", None)
            if urlpatterns is None:
                raise RuntimeError(f"{module_name} does not expose urlpatterns")
            print(f"OK  {module_name}.urlpatterns ({len(urlpatterns)} routes)")
    except Exception:
        print(f"FAIL {module_name}")
        traceback.print_exc()
        raise

from netbox_smartlock.contracts import SMARTLOCK_IMPORT_FIELD_NAMES
from netbox_smartlock.forms import SmartLockImportForm
from netbox_smartlock.exports import SmartLockExportService
from upload_file_plugin.services import MAX_UPLOAD_FILE_SIZE

if "rack_lookup" not in SmartLockImportForm.base_fields:
    raise RuntimeError("SmartLockImportForm is missing rack_lookup")
if "rack_lookup" not in SMARTLOCK_IMPORT_FIELD_NAMES:
    raise RuntimeError("SmartLock CSV contract is missing rack_lookup")
if not hasattr(SmartLockExportService, "export_excel_report"):
    raise RuntimeError("SmartLockExportService is missing Excel export")
if MAX_UPLOAD_FILE_SIZE != 25 * 1024 * 1024:
    raise RuntimeError("Upload size limit is not 25MB")

print("OK  smartlock import/export/upload contracts")
PY
'

docker compose run --rm --entrypoint /bin/sh netbox -lc '
  cd /opt/netbox/netbox &&
  /opt/netbox/venv/bin/python manage.py showmigrations >/dev/null
'

echo "Plugin bootstrap checks passed."
