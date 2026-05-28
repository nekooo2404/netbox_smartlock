from netbox.plugins import PluginConfig

class UploadFilePluginConfig(PluginConfig):
    name = 'upload_file_plugin'
    verbose_name = 'Upload File Plugin'
    description = 'Reusable image upload field for NetBox object forms'
    version = '1.0.9'
    author = 'Ngoc Anh'
    base_url = 'upload_file_plugin'

config = UploadFilePluginConfig
