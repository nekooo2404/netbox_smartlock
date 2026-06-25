####
## This file contains extra configuration options that can't be configured
## directly through environment variables.
####
from os import environ


def _as_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_list(value):
    return [item.strip() for item in str(value).replace(",", " ").split() if item.strip()]

## Specify one or more name and email address tuples representing NetBox administrators. These people will be notified of
## application errors (assuming correct email settings are provided).
# ADMINS = [
#     # ['John Doe', 'jdoe@example.com'],
# ]


## URL schemes that are allowed within links in NetBox
# ALLOWED_URL_SCHEMES = (
#     'file', 'ftp', 'ftps', 'http', 'https', 'irc', 'mailto', 'sftp', 'ssh', 'tel', 'telnet', 'tftp', 'vnc', 'xmpp',
# )

## Enable installed plugins. Add the name of each plugin to the list.
# from netbox.configuration.configuration import PLUGINS
# PLUGINS.append('my_plugin')

## Plugins configuration settings. These settings are used by various plugins that the user may have installed.
## Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
# from netbox.configuration.configuration import PLUGINS_CONFIG
# PLUGINS_CONFIG['my_plugin'] = {
#   'foo': 'bar',
#   'buzz': 'bazz'
# }


## Remote authentication support
# REMOTE_AUTH_DEFAULT_PERMISSIONS = {}

KEYCLOAK_GROUP_SYNC_ENABLED = _as_bool(environ.get("KEYCLOAK_GROUP_SYNC_ENABLED", "False"))
KEYCLOAK_GROUP_SYNC_GROUPS = _as_list(environ.get("KEYCLOAK_GROUP_SYNC_GROUPS", "Admin Guest"))
KEYCLOAK_GROUP_SYNC_REMOVE = _as_bool(environ.get("KEYCLOAK_GROUP_SYNC_REMOVE", "True"))
KEYCLOAK_GROUP_SYNC_GROUP_MAP = dict(
    item.split("=", 1)
    for item in _as_list(environ.get("KEYCLOAK_GROUP_SYNC_GROUP_MAP", "dcim-admin=Admin dcim-guest=Guest"))
    if "=" in item
)
KEYCLOAK_GROUP_SYNC_ROLE_MAP = dict(
    item.split("=", 1)
    for item in _as_list(environ.get("KEYCLOAK_GROUP_SYNC_ROLE_MAP", "dcim-admin=Admin dcim-guest=Guest"))
    if "=" in item
)
KEYCLOAK_SCOPE_SYNC_ENABLED = _as_bool(environ.get("KEYCLOAK_SCOPE_SYNC_ENABLED", "False"))
KEYCLOAK_SCOPE_SYNC_REMOVE = _as_bool(environ.get("KEYCLOAK_SCOPE_SYNC_REMOVE", "True"))
KEYCLOAK_SCOPE_SYNC_REGION_CLAIM = environ.get("KEYCLOAK_SCOPE_SYNC_REGION_CLAIM", "dcim_regions")
KEYCLOAK_SCOPE_SYNC_SITE_CLAIM = environ.get("KEYCLOAK_SCOPE_SYNC_SITE_CLAIM", "dcim_sites")
KEYCLOAK_SCOPE_SYNC_PERMISSION_PREFIX = environ.get(
    "KEYCLOAK_SCOPE_SYNC_PERMISSION_PREFIX",
    "SmartLock Keycloak Scope",
)

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "netbox.authentication.user_default_groups_handler",
    "netbox_smartlock.auth_pipeline.sync_keycloak_groups",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)


## By default uploaded media is stored on the local filesystem. Using Django-storages is also supported. Provide the
## class path of the storage driver and any configuration options in STORAGES. For example:
# STORAGES = {
#     'default': {
#         'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
#         'OPTIONS': {
#             'access_key': 'Key ID',
#             'secret_key': 'Secret',
#             'bucket_name': 'netbox',
#             'region_name': 'us-west-1',
#         }
#     },
#     'staticfiles': {
#         'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
#     }
# }


## This file can contain arbitrary Python code, e.g.:
# from datetime import datetime
# now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
# BANNER_TOP = f'<marquee width="200px">This instance started on {now}.</marquee>'
