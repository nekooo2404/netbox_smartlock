import json
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files import File as DjangoFile
from django.utils import timezone

from .models import UploadedFile

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp", "bmp")
ALLOWED_IMAGE_EXTENSION_SET = set(ALLOWED_IMAGE_EXTENSIONS)
IMAGE_ACCEPT_ATTRIBUTE = ".jpg,.jpeg,.png,.gif,.webp,.bmp,image/jpeg,image/png,image/gif,image/webp,image/bmp"
MAX_UPLOAD_FILE_SIZE = 25 * 1024 * 1024


def is_relative_to(path, parent):
    """Backport nhỏ cho Path.relative_to dạng boolean, dùng để chặn path traversal."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def get_uploaded_files(instance, model_name=None):
    """Lấy file theo model_name/object_id vì plugin dùng được cho nhiều model khác nhau."""
    if not instance or not instance.pk:
        return UploadedFile.objects.none()

    return UploadedFile.objects.filter(
        model_name=model_name or instance._meta.model_name,
        object_id=instance.pk,
    ).order_by("created_at", "pk")


def serialize_uploaded_file(file_obj):
    """Chuẩn hóa metadata file để widget upload có thể render lại file đã lưu."""
    try:
        size = file_obj.file.size
    except (OSError, ValueError):
        size = 0

    return {
        "id": file_obj.pk,
        "file_name": file_obj.file_name or Path(file_obj.file.name).name,
        "path": file_obj.file.name,
        "size": size,
        "created_at": timezone.localtime(file_obj.created_at).strftime("%Y-%m-%d %H:%M"),
        "is_from_db": True,
    }


def safe_delete_uploaded_file(file_obj):
    """Xóa cả file storage và record DB, vẫn dọn DB nếu storage delete lỗi."""
    try:
        storage_name = file_obj.file.name
        if storage_name:
            file_obj.file.delete(save=False)
    finally:
        file_obj.delete()


def delete_uploaded_files(instance, model_name=None):
    for file_obj in get_uploaded_files(instance, model_name=model_name):
        safe_delete_uploaded_file(file_obj)


def is_allowed_image(file_name):
    return Path(file_name or "").suffix.lower().lstrip(".") in ALLOWED_IMAGE_EXTENSION_SET


def is_allowed_size(file_size):
    return file_size <= MAX_UPLOAD_FILE_SIZE


def resolve_temp_upload_path(raw_path):
    """Chỉ resolve file nằm trong MEDIA_ROOT/uploads/tmp để tránh xóa/đọc ngoài vùng tạm."""
    if not raw_path:
        return None

    media_root = Path(settings.MEDIA_ROOT).resolve()
    tmp_root = (media_root / "uploads" / "tmp").resolve()
    media_url = getattr(settings, "MEDIA_URL", "/media/")

    if raw_path.startswith(media_url):
        candidate = media_root / raw_path[len(media_url):].lstrip("/")
    elif raw_path.startswith("/"):
        return None
    else:
        candidate = media_root / raw_path.lstrip("/")

    resolved = candidate.resolve()
    if not is_relative_to(resolved, tmp_root):
        return None
    if not resolved.is_file():
        return None

    return resolved


@dataclass(frozen=True)
class PendingUpload:
    """File tạm đã qua validate và chờ chuyển sang thư mục upload chính."""

    file_name: str
    temp_path: Path


class AttachmentSyncService:
    """Đồng bộ JSON từ widget thành UploadedFile thật của object đã lưu."""

    def __init__(self, instance, *, model_name=None):
        self.instance = instance
        self.model_name = model_name or instance._meta.model_name
        self.content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)

    def sync_from_json(self, all_files_json):
        """Giữ file cũ còn trong payload, xóa file bị bỏ, và persist file tạm mới."""
        if not self.instance or not self.instance.pk:
            return

        files = self._parse_payload(all_files_json)
        if files is None:
            return

        existing_by_id = {
            file_obj.pk: file_obj
            for file_obj in UploadedFile.objects.filter(
                model_name=self.model_name,
                object_id=self.instance.pk,
            )
        }
        retained_ids, pending_uploads = self._classify_payload(files, existing_by_id)
        self._delete_removed_files(existing_by_id, retained_ids)
        self._persist_pending_uploads(pending_uploads)

    def _parse_payload(self, all_files_json):
        try:
            files = json.loads(all_files_json or "[]")
        except json.JSONDecodeError:
            logger.warning(
                "Invalid upload file payload for %s %s",
                self.instance._meta.label,
                self.instance.pk,
            )
            return None

        if not isinstance(files, list):
            return None
        return files

    def _classify_payload(self, files, existing_by_id):
        """Tách payload thành file cũ cần giữ và file tạm cần persist."""
        retained_ids = set()
        pending_uploads = []

        for item in files:
            if not isinstance(item, dict):
                continue

            file_id = self._coerce_file_id(item.get("id"))
            if file_id in existing_by_id:
                retained_ids.add(file_id)
                continue

            pending_upload = self._build_pending_upload(item)
            if pending_upload:
                pending_uploads.append(pending_upload)

        return retained_ids, pending_uploads

    @staticmethod
    def _coerce_file_id(value):
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _build_pending_upload(self, item):
        """Validate extension, path tạm và dung lượng trước khi persist file."""
        file_name = item.get("file_name") or item.get("name")
        raw_path = item.get("path") or ""

        if not is_allowed_image(file_name):
            logger.warning(
                "Rejected non-image upload payload for %s %s: %s",
                self.instance._meta.label,
                self.instance.pk,
                file_name,
            )
            return None

        temp_path = resolve_temp_upload_path(raw_path)
        if not (file_name and temp_path):
            return None

        try:
            file_size = temp_path.stat().st_size
        except OSError:
            file_size = None

        if file_size is None or not is_allowed_size(file_size):
            logger.warning(
                "Rejected oversized upload payload for %s %s: %s",
                self.instance._meta.label,
                self.instance.pk,
                file_name,
            )
            return None

        return PendingUpload(file_name=file_name, temp_path=temp_path)

    @staticmethod
    def _delete_removed_files(existing_by_id, retained_ids):
        for file_id, file_obj in existing_by_id.items():
            if file_id not in retained_ids:
                safe_delete_uploaded_file(file_obj)

    def _persist_pending_uploads(self, pending_uploads):
        """Lưu file bằng tên UUID để tránh đè file và xóa bản tạm sau khi lưu thành công."""
        upload_subdir = f"uploads/{self.model_name}"

        for pending in pending_uploads:
            base_name = pending.temp_path.stem
            extension = pending.temp_path.suffix
            stored_name = f"{upload_subdir}/{base_name}_{uuid.uuid4().hex}{extension}"

            try:
                with pending.temp_path.open("rb") as handle:
                    uploaded_file = UploadedFile(
                        file_name=pending.file_name,
                        content_type=self.content_type,
                        object_id=self.instance.pk,
                        model_name=self.model_name,
                    )
                    uploaded_file.file.save(stored_name, DjangoFile(handle), save=True)
                os.remove(pending.temp_path)
            except OSError as exc:
                logger.error(
                    "Could not save uploaded file %s for %s: %s",
                    pending.temp_path,
                    self.instance,
                    exc,
                )


def sync_uploaded_files(instance, all_files_json, model_name=None):
    if not instance:
        return
    AttachmentSyncService(instance, model_name=model_name).sync_from_json(all_files_json)
