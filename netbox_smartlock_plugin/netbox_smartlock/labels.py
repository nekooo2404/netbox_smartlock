MODEL_LABELS = {
    "assetgroup": {
        "singular": "Nhóm tài sản",
        "plural": "Nhóm tài sản",
    },
    "asset": {
        "singular": "Tài sản",
        "plural": "Tài sản",
    },
    "smartlock": {
        "singular": "Khóa thông minh",
        "plural": "Khóa thông minh",
    },
    "accessrequest": {
        "singular": "Phiếu yêu cầu vào ra",
        "plural": "Phiếu yêu cầu vào ra",
    },
    "accessrequestperson": {
        "singular": "Đối tượng vào ra",
        "plural": "Đối tượng vào ra",
    },
}


def model_label(model_or_instance, *, plural=False):
    """Lấy tên model tiếng Việt cho template custom mà không đổi verbose_name DB/API."""
    meta = getattr(model_or_instance, "_meta", None)
    key = getattr(meta, "model_name", "")
    labels = MODEL_LABELS.get(key, {})
    if plural:
        return labels.get("plural", getattr(meta, "verbose_name_plural", ""))
    return labels.get("singular", getattr(meta, "verbose_name", ""))


def apply_model_label_context(context, model_or_instance):
    """Đưa label model vào context theo key riêng để không đè context gốc của NetBox."""
    context["smartlock_model_label"] = model_label(model_or_instance)
    context["smartlock_model_label_plural"] = model_label(model_or_instance, plural=True)
    return context
