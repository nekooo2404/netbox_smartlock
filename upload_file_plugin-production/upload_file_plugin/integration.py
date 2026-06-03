import json

from django import forms

from .services import (
    ALLOWED_IMAGE_EXTENSIONS,
    IMAGE_ACCEPT_ATTRIBUTE,
    MAX_UPLOAD_FILE_SIZE,
    delete_uploaded_files,
    get_uploaded_files,
    serialize_uploaded_file,
    sync_uploaded_files,
)


class UploadFileWidget(forms.Widget):
    """Widget trung gian giữ JSON payload để form chính tự đồng bộ file sau khi save."""

    template_name = "upload_file/widgets/upload_file.html"

    def __init__(self, *, instance=None, model_name=None, valid_flg="0", type_file=None, attrs=None):
        super().__init__(attrs)
        self.instance = instance
        self.model_name = model_name
        self.valid_flg = valid_flg
        self.type_file = type_file

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        model_name = self.model_name or (self.instance._meta.model_name if self.instance else "")
        initial_files = [
            serialize_uploaded_file(file_obj)
            for file_obj in get_uploaded_files(self.instance, model_name=model_name)
        ]
        field_id = attrs.get("id", name) if attrs else name
        type_file = self.type_file if self.type_file is not None else ALLOWED_IMAGE_EXTENSIONS
        if not isinstance(type_file, str):
            type_file = json.dumps(list(type_file))

        context["widget"].update(
            {
                "accept": IMAGE_ACCEPT_ATTRIBUTE,
                "object_id": self.instance.pk if self.instance and self.instance.pk else "",
                "model_name": model_name,
                "valid_flg": self.valid_flg,
                "type_file": type_file,
                "initial_files_json": initial_files,
                "initial_files_script_id": f"{field_id}-initial-files",
            }
        )
        return context

    def value_from_datadict(self, data, files, name):
        return data.get(name, data.get("all_files", "[]"))


class UploadFileFormMixin:
    """Mixin thêm field upload tái sử dụng cho các NetBox model form."""

    upload_file_field_name = "upload_files"
    upload_file_label = "Attachments"
    upload_file_model_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_name = self.upload_file_model_name
        if not model_name and getattr(self, "instance", None):
            model_name = self.instance._meta.model_name
        self.fields[self.upload_file_field_name] = forms.CharField(
            required=False,
            label=self.upload_file_label,
            widget=UploadFileWidget(
                instance=getattr(self, "instance", None),
                model_name=model_name,
            ),
        )

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        model_name = self.upload_file_model_name or instance._meta.model_name
        sync_uploaded_files(instance, self.cleaned_data.get(self.upload_file_field_name, "[]"), model_name=model_name)
        return instance
