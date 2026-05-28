import json
import logging
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .services import ALLOWED_IMAGE_EXTENSIONS, MAX_UPLOAD_FILE_SIZE

logger = logging.getLogger(__name__)

VALID_MEDIA_TYPES = list(ALLOWED_IMAGE_EXTENSIONS)


def _file_extension(file_name):
    return os.path.splitext(file_name or "")[1].lower().lstrip(".")


def _parse_allowed_file_types(raw_value):
    if not raw_value:
        return []

    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value.replace("[", "").replace("]", "").split(",")

    if not isinstance(value, list):
        return []

    return [
        str(item).strip().strip('"\'').lower().lstrip(".")
        for item in value
        if str(item).strip()
    ]


def _image_type_error(file_name, file_type):
    name = os.path.splitext(file_name or "Unnamed file")[0]
    suffix = f" ({file_type})" if file_type else ""
    return f"File '{name}'{suffix} must be an image: {', '.join(VALID_MEDIA_TYPES)}."


def _file_size_error(file_name):
    name = os.path.splitext(file_name or "Unnamed file")[0]
    return f"File '{name}' exceeds the 25MB limit."


def _json_login_required(request):
    if request.user.is_authenticated:
        return None
    return JsonResponse(
        {"success": False, "errors": ["Authentication is required. Please reload the page and sign in again."]},
        status=401,
    )


@require_http_methods(["POST"])
def upload_file_view(request):
    if response := _json_login_required(request):
        return response

    files = request.FILES.getlist("files")
    valid_flg_str = request.POST.get("valid_flg", "0")
    validate_enabled = valid_flg_str == "1"
    type_file_json_str = request.POST.get("type_file", "[]")

    errors = []
    saved_files = []
    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads", "tmp")
    os.makedirs(upload_dir, exist_ok=True)

    for uploaded in files:
        is_file_valid = True
        validation_error_message = ""

        name, ext = os.path.splitext(uploaded.name)
        file_type = _file_extension(uploaded.name)

        if file_type not in VALID_MEDIA_TYPES:
            is_file_valid = False
            validation_error_message = _image_type_error(uploaded.name, file_type)

        if is_file_valid and uploaded.size > MAX_UPLOAD_FILE_SIZE:
            is_file_valid = False
            validation_error_message = _file_size_error(uploaded.name)

        if is_file_valid and validate_enabled:
            allowed_file_types = _parse_allowed_file_types(type_file_json_str)
            if file_type not in allowed_file_types:
                validation_error_message = (
                    f"File '{name}' is not one of the allowed formats: "
                    f"{', '.join(allowed_file_types)}."
                )
                is_file_valid = False

        if not is_file_valid:
            errors.append(validation_error_message)
            logger.warning("File '%s' was rejected: %s", name, validation_error_message)
            continue

        new_file_name = f"{name}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, new_file_name)

        try:
            with open(file_path, "wb+") as destination:
                for chunk in uploaded.chunks():
                    destination.write(chunk)
            saved_files.append({
                "file_name": uploaded.name,
                "size": uploaded.size,
                "path": settings.MEDIA_URL.rstrip("/") + f"/uploads/tmp/{new_file_name}",
            })
            logger.info("Uploaded file: %s -> %s", uploaded.name, file_path)
        except OSError as exc:
            logger.error("Failed to upload file %s: %s", uploaded.name, exc)
            errors.append(f"Failed to save file '{uploaded.name}': {exc}")

    return JsonResponse({
        "saved_files": saved_files,
        "errors": errors,
        "success": bool(saved_files) and not errors if files else False,
    })


@require_http_methods(["POST"])
def delete_temp_file_view(request):
    if response := _json_login_required(request):
        return response

    try:
        file_name = request.POST.get("file_name")
        file_path = request.POST.get("path")
        if not file_name or not file_path:
            return JsonResponse({"success": False, "error": "Missing file_name or path"}, status=400)

        allowed_dir = (Path(settings.MEDIA_ROOT) / "uploads" / "tmp").resolve()
        media_url = settings.MEDIA_URL.rstrip("/") + "/"
        if file_path.startswith(media_url):
            relative_path = file_path[len(media_url):].lstrip("/")
            candidate_path = Path(settings.MEDIA_ROOT) / relative_path
        elif file_path.startswith("/"):
            return JsonResponse({"success": False, "error": "Invalid file path"}, status=400)
        else:
            candidate_path = Path(settings.MEDIA_ROOT) / file_path.lstrip("/")

        abs_file_path = candidate_path.resolve()
        try:
            abs_file_path.relative_to(allowed_dir)
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid file path"}, status=400)

        if abs_file_path.exists():
            try:
                abs_file_path.unlink()
                logger.info("Deleted temp file: %s", abs_file_path)
                return JsonResponse({"success": True})
            except OSError as exc:
                logger.error("Error deleting temp file: %s", exc)
                return JsonResponse({"success": False, "error": str(exc)}, status=500)

        return JsonResponse({"success": False, "error": "File does not exist"}, status=404)
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
