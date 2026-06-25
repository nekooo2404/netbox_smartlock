from django.test import SimpleTestCase

from upload_file_plugin.services import (
    ALLOWED_IMAGE_EXTENSIONS,
    IMAGE_ACCEPT_ATTRIBUTE,
    MAX_UPLOAD_FILE_SIZE,
    is_allowed_image,
    is_allowed_size,
)


class UploadFileServiceContractTest(SimpleTestCase):
    def test_image_extension_contract(self):
        self.assertEqual(ALLOWED_IMAGE_EXTENSIONS, ("jpg", "jpeg", "png"))
        self.assertIn("image/png", IMAGE_ACCEPT_ATTRIBUTE)
        self.assertTrue(is_allowed_image("door.PNG"))
        self.assertFalse(is_allowed_image("door.webp"))
        self.assertFalse(is_allowed_image("door.pdf"))

    def test_upload_size_limit_contract(self):
        self.assertEqual(MAX_UPLOAD_FILE_SIZE, 25 * 1024 * 1024)
        self.assertTrue(is_allowed_size(MAX_UPLOAD_FILE_SIZE))
        self.assertFalse(is_allowed_size(MAX_UPLOAD_FILE_SIZE + 1))

