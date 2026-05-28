$ErrorActionPreference = "Stop"

Write-Host "Checking NetBox plugin bootstrap..."

$pythonCheck = @'
cd /opt/netbox/netbox &&
cat <<'PY' >/tmp/check_plugin_bootstrap.py
import importlib

checks = [
    'netbox_smartlock.urls',
    'netbox_smartlock.views',
    'netbox_smartlock.forms',
    'netbox_smartlock.contracts',
    'netbox_smartlock.exports',
    'netbox_smartlock.services',
    'upload_file_plugin.integration',
    'upload_file_plugin.services',
]

for module_name in checks:
    importlib.import_module(module_name)
    print('OK  {}'.format(module_name))

urls = importlib.import_module('netbox_smartlock.urls')
patterns = getattr(urls, 'urlpatterns', None)
if patterns is None:
    raise RuntimeError('netbox_smartlock.urls does not expose urlpatterns')

print('OK  netbox_smartlock.urls.urlpatterns ({} routes)'.format(len(patterns)))

from netbox_smartlock.contracts import SMARTLOCK_IMPORT_FIELD_NAMES
from netbox_smartlock.forms import SmartLockImportForm
from netbox_smartlock.exports import SmartLockExportService
from upload_file_plugin.services import MAX_UPLOAD_FILE_SIZE

if 'rack_lookup' not in SmartLockImportForm.base_fields:
    raise RuntimeError('SmartLockImportForm is missing rack_lookup')
if 'rack_lookup' not in SMARTLOCK_IMPORT_FIELD_NAMES:
    raise RuntimeError('SmartLock CSV contract is missing rack_lookup')
if not hasattr(SmartLockExportService, 'export_excel_report'):
    raise RuntimeError('SmartLockExportService is missing Excel export')
if MAX_UPLOAD_FILE_SIZE != 25 * 1024 * 1024:
    raise RuntimeError('Upload size limit is not 25MB')

print('OK  smartlock import/export/upload contracts')
PY
/opt/netbox/venv/bin/python manage.py shell --interface python --no-startup --no-imports </tmp/check_plugin_bootstrap.py
'@

docker compose run --rm --entrypoint /bin/sh netbox -lc $pythonCheck
docker compose run --rm --entrypoint /bin/sh netbox -lc 'cd /opt/netbox/netbox && /opt/netbox/venv/bin/python manage.py showmigrations >/dev/null'

Write-Host "Plugin bootstrap checks passed."
