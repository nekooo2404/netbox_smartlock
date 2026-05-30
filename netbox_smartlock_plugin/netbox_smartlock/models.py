import calendar
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse

from core.choices import ObjectChangeActionChoices
from core.models.change_logging import ObjectChange
from dcim.models import Location, Rack, Region, Site
from netbox.models import NetBoxModel, OrganizationalModel
from upload_file_plugin.integration import delete_uploaded_files

from .mapping import normalize_text, sync_smartlock_hierarchy
from .messages import (
    ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_VERIFY_REQUIRES_CONFIRMED_MESSAGE,
)
from .ui import (
    ACCESS_REQUEST_HISTORY_ACTION_LABELS,
    ACCESS_REQUEST_PERSON_ACCESS_LABELS,
    ACCESS_REQUEST_PERSON_VERIFY_LABELS,
    ACCESS_REQUEST_STATUS_LABELS,
    ASSET_GROUP_STATUS_LABELS,
    RACK_FACE_LABELS,
    SMARTLOCK_STATUS_LABELS,
    label_for,
)


def validate_file_size(value):
    """Giữ lại cho các migration cũ từng tham chiếu field attachment legacy."""
    max_size = 25 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError("File đính kèm không được vượt quá 25MB.")


def add_months(value, months):
    """Cộng tháng theo lịch, tự kẹp ngày cuối tháng để tính hạn bảo hành ổn định."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class AssetGroup(OrganizationalModel):
    """Nhóm phân loại tài sản SmartLock."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    )

    name = models.CharField(max_length=100, unique=True, verbose_name="Name")
    slug = models.SlugField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Code")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name="Status",
    )
    description = models.TextField(blank=True, verbose_name="Description")
    comments = models.TextField(blank=True, default="", verbose_name="Comments")

    class Meta:
        ordering = ("name",)
        verbose_name = "Asset Group"
        verbose_name_plural = "Asset Groups"

    def __str__(self):
        return self.name

    @property
    def status_label(self):
        return label_for(ASSET_GROUP_STATUS_LABELS, self.status)

    def get_absolute_url(self):
        return reverse("plugins:netbox_smartlock:assetgroup", kwargs={"pk": self.pk})

    def get_edit_url(self):
        return reverse("plugins:netbox_smartlock:assetgroup_edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("plugins:netbox_smartlock:assetgroup_delete", kwargs={"pk": self.pk})

    def delete(self, *args, **kwargs):
        delete_uploaded_files(self, model_name="assetgroup")
        return super().delete(*args, **kwargs)


class SmartLock(NetBoxModel):
    """Thiết bị khóa thông minh gắn với cây vị trí DCIM của NetBox."""

    STATUS_ACTIVE = "active"
    STATUS_BACKUP = "backup"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_BROKEN = "broken"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_BACKUP, "Backup"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_BROKEN, "Broken"),
    )
    RACK_FACE_FRONT = "front"
    RACK_FACE_REAR = "rear"
    RACK_FACE_CHOICES = (
        (RACK_FACE_FRONT, "Front"),
        (RACK_FACE_REAR, "Rear"),
    )

    name = models.CharField(max_length=100, verbose_name="Name")
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    asset_group = models.ForeignKey(
        AssetGroup,
        on_delete=models.PROTECT,
        related_name="smartlocks",
        verbose_name="Asset Group",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name="Status",
    )
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500)],
        verbose_name="Description",
    )
    comments = models.TextField(blank=True, default="", verbose_name="Comments")

    device_type = models.CharField(max_length=100, verbose_name="Device Type")
    model = models.CharField(max_length=100, blank=True, verbose_name="Model")
    serial = models.CharField(max_length=100, blank=True, verbose_name="Serial")
    manufacturer = models.CharField(max_length=100, blank=True, verbose_name="Manufacturer")

    setup_date = models.DateField(blank=True, null=True, verbose_name="Setup Date")
    bought_date = models.DateField(blank=True, null=True, verbose_name="Purchase Date")
    warranty_period = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Unit: months",
        verbose_name="Warranty Period",
    )
    warranty_expiration_date = models.DateField(
        blank=True,
        null=True,
        editable=False,
        verbose_name="Warranty Expiration Date",
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="smartlocks",
        verbose_name="Region",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="smartlocks",
        verbose_name="Site",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="smartlocks",
        verbose_name="Location",
    )
    rack = models.ForeignKey(
        Rack,
        on_delete=models.PROTECT,
        related_name="smartlocks",
        blank=True,
        null=True,
        verbose_name="Rack",
    )
    rack_face = models.CharField(
        max_length=10,
        choices=RACK_FACE_CHOICES,
        blank=True,
        verbose_name="Rack Face",
    )

    clone_fields = (
        "asset_group", "status", "device_type", "model",
        "manufacturer", "region", "site", "location", "rack", "rack_face",
    )

    class Meta:
        ordering = ("-last_updated", "name")
        verbose_name = "Smart Lock"
        verbose_name_plural = "Smart Locks"

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def status_label(self):
        return label_for(SMARTLOCK_STATUS_LABELS, self.status)

    @property
    def rack_face_label(self):
        return label_for(RACK_FACE_LABELS, self.rack_face)

    def get_absolute_url(self):
        return reverse("plugins:netbox_smartlock:smartlock", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        errors = {}

        if self.rack_face and not self.rack_id:
            errors["rack"] = "Vui lòng chọn tủ rack trước khi chọn mặt tủ rack."

        # Rack/Location/Site/Region là dữ liệu DCIM gốc của NetBox; plugin chỉ đồng bộ tham chiếu.
        sync_smartlock_hierarchy(self, errors=errors)

        if self.warranty_period is not None and not self.bought_date:
            errors["bought_date"] = "Bắt buộc nhập ngày mua khi thiết lập thời hạn bảo hành."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = normalize_text(self.name)
        self.code = normalize_text(self.code)
        self.device_type = normalize_text(self.device_type)
        self.model = normalize_text(self.model)
        self.serial = normalize_text(self.serial)
        self.manufacturer = normalize_text(self.manufacturer)

        self.full_clean()

        if self.bought_date and self.warranty_period is not None:
            self.warranty_expiration_date = add_months(self.bought_date, self.warranty_period)
        else:
            self.warranty_expiration_date = None

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        delete_uploaded_files(self, model_name="smartlock")
        return super().delete(*args, **kwargs)


class AccessRequest(NetBoxModel):
    """Phiếu Guest yêu cầu vào ra một địa điểm DCIM."""

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_CONFIRMED = "confirmed"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_COMPLETED, "Completed"),
    )
    GUEST_LOCKED_STATUSES = (STATUS_ACCEPTED, STATUS_COMPLETED)
    SUBMITTABLE_STATUSES = (STATUS_DRAFT, STATUS_REJECTED)

    name = models.CharField(max_length=100, unique=True, verbose_name="Request Name")
    expected_date = models.DateField(verbose_name="Expected Date")
    reason = models.TextField(validators=[MaxLengthValidator(500)], verbose_name="Reason")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="Status",
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="access_requests",
        blank=True,
        null=True,
        verbose_name="Region",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="access_requests",
        blank=True,
        null=True,
        verbose_name="Site",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="access_requests",
        blank=True,
        null=True,
        editable=False,
        verbose_name="Created By",
    )

    clone_fields = ("expected_date", "reason", "region", "site")

    class Meta:
        ordering = ("-last_updated", "name")
        verbose_name = "Access Request"
        verbose_name_plural = "Access Requests"

    def __str__(self):
        return self.name

    @property
    def status_label(self):
        return label_for(ACCESS_REQUEST_STATUS_LABELS, self.status)

    @property
    def can_guest_edit(self):
        return self.status not in self.GUEST_LOCKED_STATUSES

    @property
    def can_guest_delete(self):
        return self.status not in self.GUEST_LOCKED_STATUSES

    @property
    def can_submit(self):
        if self.status not in self.SUBMITTABLE_STATUSES:
            return False
        if not self.pk:
            return False
        return self.persons.exists()

    @property
    def can_admin_confirm(self):
        return self.status == self.STATUS_SUBMITTED

    @property
    def can_admin_decide(self):
        return self.status == self.STATUS_CONFIRMED

    @property
    def can_admin_complete(self):
        return self.status == self.STATUS_ACCEPTED

    def get_absolute_url(self):
        return reverse("plugins:netbox_smartlock:accessrequest", kwargs={"pk": self.pk})

    def get_edit_url(self):
        return reverse("plugins:netbox_smartlock:accessrequest_edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("plugins:netbox_smartlock:accessrequest_delete", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        errors = {}

        if self.site_id and self.region_id and self.site.region_id != self.region_id:
            errors["site"] = "Địa điểm đã chọn phải thuộc khu vực đã chọn."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = normalize_text(self.name)
        self.reason = normalize_text(self.reason)
        self.full_clean()
        return super().save(*args, **kwargs)

    def submit(self, user=None, description=""):
        if not self.can_submit:
            raise ValidationError("Phiếu yêu cầu phải có ít nhất một đối tượng và còn được phép sửa trước khi gửi.")

        self.status = self.STATUS_SUBMITTED
        self.save(update_fields=("status", "last_updated"))
        history = AccessRequestHistory.record(
            request=self,
            actor=user,
            action=AccessRequestHistory.ACTION_SUBMIT,
            status=self.status,
            description=description,
        )
        notify_access_request_admins(self, submitted_by=user)
        return history

    def confirm(self, user=None, description=""):
        if not self.can_admin_confirm:
            raise ValidationError("Admin chỉ được xác nhận phiếu yêu cầu đã gửi.")

        self.status = self.STATUS_CONFIRMED
        self.save(update_fields=("status", "last_updated"))
        return AccessRequestHistory.record(
            request=self,
            actor=user,
            action=AccessRequestHistory.ACTION_CONFIRM,
            status=self.status,
            description=description,
        )

    def accept(self, user=None, description=""):
        if not self.can_admin_decide:
            raise ValidationError("Chỉ phiếu yêu cầu đã xác nhận mới được chấp nhận.")
        # Không chấp nhận phiếu khi còn bất kỳ đối tượng nào chưa được Admin xác minh hợp lệ.
        if self.persons.filter(verify_status=AccessRequestPerson.VERIFY_INVALID).exists():
            raise ValidationError("Không thể chấp nhận phiếu yêu cầu có đối tượng không hợp lệ.")
        if self.persons.exclude(verify_status=AccessRequestPerson.VERIFY_VALID).exists():
            raise ValidationError("Tất cả đối tượng phải được xác minh hợp lệ trước khi chấp nhận phiếu yêu cầu.")

        self.status = self.STATUS_ACCEPTED
        self.save(update_fields=("status", "last_updated"))
        history = AccessRequestHistory.record(
            request=self,
            actor=user,
            action=AccessRequestHistory.ACTION_ACCEPT,
            status=self.status,
            description=description,
        )
        notify_access_request_creator(
            self,
            subject=f"Phiếu yêu cầu đã được chấp nhận: {self.name}",
            message=f"Phiếu yêu cầu {self.name} đã được chấp nhận.\nMô tả: {description or '-'}",
        )
        return history

    def reject(self, user=None, description=""):
        if self.status != self.STATUS_CONFIRMED:
            raise ValidationError("Chỉ phiếu yêu cầu đã xác nhận mới được từ chối.")
        if not normalize_text(description):
            raise ValidationError("Bắt buộc nhập lý do từ chối.")

        self.status = self.STATUS_REJECTED
        self.save(update_fields=("status", "last_updated"))
        history = AccessRequestHistory.record(
            request=self,
            actor=user,
            action=AccessRequestHistory.ACTION_REJECT,
            status=self.status,
            description=description,
        )
        notify_access_request_creator(
            self,
            subject=f"Phiếu yêu cầu đã bị từ chối: {self.name}",
            message=f"Phiếu yêu cầu {self.name} đã bị từ chối.\nLý do: {description or '-'}",
        )
        return history

    def complete(self, user=None, description=""):
        if not self.can_admin_complete:
            raise ValidationError("Chỉ phiếu yêu cầu đã chấp nhận mới được hoàn thành.")

        self.status = self.STATUS_COMPLETED
        self.save(update_fields=("status", "last_updated"))
        history = AccessRequestHistory.record(
            request=self,
            actor=user,
            action=AccessRequestHistory.ACTION_COMPLETE,
            status=self.status,
            description=description,
        )
        notify_access_request_creator(
            self,
            subject=f"Phiếu yêu cầu đã hoàn thành: {self.name}",
            message=f"Phiếu yêu cầu {self.name} đã hoàn thành.",
        )
        return history

    def delete(self, *args, **kwargs):
        if not self.can_guest_delete:
            raise ValidationError(ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE)
        return super().delete(*args, **kwargs)


class AccessRequestPerson(NetBoxModel):
    """Đối tượng vào ra do Guest khai báo trong một phiếu yêu cầu."""

    VIETNAMESE_MOBILE_PREFIXES = ("03", "05", "07", "08", "09")

    VERIFY_PENDING = "pending"
    VERIFY_VALID = "valid"
    VERIFY_INVALID = "invalid"
    ACCESS_OUT = "out"
    ACCESS_IN = "in"

    VERIFY_STATUS_CHOICES = (
        (VERIFY_PENDING, "Pending"),
        (VERIFY_VALID, "Valid"),
        (VERIFY_INVALID, "Invalid"),
    )
    ACCESS_STATUS_CHOICES = (
        (ACCESS_OUT, "Out"),
        (ACCESS_IN, "In"),
    )
    GUEST_MUTABLE_VERIFY_STATUSES = (VERIFY_PENDING, VERIFY_INVALID)

    request = models.ForeignKey(
        AccessRequest,
        on_delete=models.CASCADE,
        related_name="persons",
        verbose_name="Access Request",
    )
    identity_code = models.CharField(max_length=12, verbose_name="Identity Code")
    full_name = models.CharField(max_length=50, verbose_name="Full Name")
    organization = models.CharField(max_length=100, verbose_name="Organization")
    title = models.CharField(max_length=50, blank=True, verbose_name="Title")
    phone = models.CharField(max_length=10, blank=True, verbose_name="Phone")
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="access_request_persons",
        blank=True,
        null=True,
        verbose_name="Location",
    )
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500)],
        verbose_name="Description",
    )
    verify_status = models.CharField(
        max_length=20,
        choices=VERIFY_STATUS_CHOICES,
        default=VERIFY_PENDING,
        verbose_name="Verification Status",
    )
    access_status = models.CharField(
        max_length=10,
        choices=ACCESS_STATUS_CHOICES,
        default=ACCESS_OUT,
        verbose_name="Access Status",
    )

    clone_fields = ("request", "organization", "title", "phone", "location")

    class Meta:
        ordering = ("-last_updated", "full_name")
        verbose_name = "Access Request Person"
        verbose_name_plural = "Access Request Persons"
        constraints = (
            models.UniqueConstraint(
                fields=("request", "identity_code"),
                name="netbox_smartlock_accessrequestperson_unique_request_identity",
            ),
        )

    def __str__(self):
        return self.full_name

    @property
    def verify_status_label(self):
        return label_for(ACCESS_REQUEST_PERSON_VERIFY_LABELS, self.verify_status)

    @property
    def access_status_label(self):
        return label_for(ACCESS_REQUEST_PERSON_ACCESS_LABELS, self.access_status)

    def request_has_status(self, *statuses):
        """Kiểm tra trạng thái phiếu bằng queryset để không phụ thuộc object request đã prefetch."""
        if not self.request_id:
            return False
        return AccessRequest.objects.filter(pk=self.request_id, status__in=statuses).exists()

    @property
    def can_guest_edit(self):
        if not self.request_id:
            return False

        if self.request_has_status(AccessRequest.STATUS_REJECTED):
            return True

        return bool(
            self.verify_status in self.GUEST_MUTABLE_VERIFY_STATUSES
            and not self.request_has_status(*AccessRequest.GUEST_LOCKED_STATUSES)
        )

    @property
    def can_guest_delete(self):
        if not self.request_id:
            return False

        return bool(
            self.request_has_status(AccessRequest.STATUS_REJECTED)
            or self.request_has_status(AccessRequest.STATUS_ACCEPTED)
            or (
                self.verify_status in self.GUEST_MUTABLE_VERIFY_STATUSES
                and not self.request_has_status(*AccessRequest.GUEST_LOCKED_STATUSES)
            )
        )

    @property
    def can_admin_verify(self):
        return self.request_has_status(AccessRequest.STATUS_CONFIRMED)

    @property
    def can_mark_in(self):
        return bool(
            self.request_has_status(AccessRequest.STATUS_ACCEPTED)
            and self.verify_status == self.VERIFY_VALID
            and self.access_status == self.ACCESS_OUT
        )

    @property
    def can_mark_out(self):
        return bool(
            self.request_has_status(AccessRequest.STATUS_ACCEPTED)
            and self.verify_status == self.VERIFY_VALID
            and self.access_status == self.ACCESS_IN
        )

    def get_absolute_url(self):
        return reverse("plugins:netbox_smartlock:accessrequestperson", kwargs={"pk": self.pk})

    def get_edit_url(self):
        return reverse("plugins:netbox_smartlock:accessrequestperson_edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("plugins:netbox_smartlock:accessrequestperson_delete", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        errors = {}

        if self.identity_code and (len(self.identity_code) != 12 or not self.identity_code.isdigit()):
            errors["identity_code"] = "CCCD/CMND phải gồm đúng 12 chữ số."

        if self.phone and (
            len(self.phone) != 10
            or not self.phone.isdigit()
            or not self.phone.startswith(self.VIETNAMESE_MOBILE_PREFIXES)
        ):
            errors["phone"] = "Số điện thoại phải là số di động Việt Nam hợp lệ gồm 10 chữ số."

        if self.location_id and self.request_id and self.location.site_id != self.request.site_id:
            errors["location"] = "Vị trí đã chọn phải thuộc địa điểm của phiếu yêu cầu."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.identity_code = normalize_text(self.identity_code)
        self.full_name = normalize_text(self.full_name)
        self.organization = normalize_text(self.organization)
        self.title = normalize_text(self.title)
        self.phone = normalize_text(self.phone)
        self.description = normalize_text(self.description)
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self.can_guest_delete:
            raise ValidationError(ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE)
        return super().delete(*args, **kwargs)

    def mark_valid(self, user=None, description=""):
        if not self.can_admin_verify:
            raise ValidationError(ACCESS_REQUEST_PERSON_VERIFY_REQUIRES_CONFIRMED_MESSAGE)

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.verify_status = self.VERIFY_VALID
        self.save(update_fields=("verify_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_VERIFY_VALID,
            status=access_request.status,
            description=description or f"Đánh dấu {self.full_name} là hợp lệ.",
        )

    def mark_invalid(self, user=None, description=""):
        if not self.can_admin_verify:
            raise ValidationError(ACCESS_REQUEST_PERSON_VERIFY_REQUIRES_CONFIRMED_MESSAGE)

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.verify_status = self.VERIFY_INVALID
        self.save(update_fields=("verify_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_VERIFY_INVALID,
            status=access_request.status,
            description=description or f"Đánh dấu {self.full_name} là không hợp lệ.",
        )

    def mark_in(self, user=None, description=""):
        if not self.can_mark_in:
            raise ValidationError("Chỉ đối tượng hợp lệ trong phiếu đã chấp nhận mới được chuyển từ Out sang In.")

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.access_status = self.ACCESS_IN
        self.save(update_fields=("access_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_IN,
            status=access_request.status,
            description=description or f"Out -> In: {self.full_name}.",
        )

    def mark_out(self, user=None, description=""):
        if not self.can_mark_out:
            raise ValidationError("Chỉ đối tượng trong phiếu đã chấp nhận mới được chuyển từ In sang Out.")

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.access_status = self.ACCESS_OUT
        self.save(update_fields=("access_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_OUT,
            status=access_request.status,
            description=description or f"In -> Out: {self.full_name}.",
        )


class AccessRequestHistory(models.Model):
    """Lịch sử nghiệp vụ riêng cho workflow phiếu yêu cầu vào ra."""

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_SUBMIT = "submit"
    ACTION_CONFIRM = "confirm"
    ACTION_ACCEPT = "accept"
    ACTION_REJECT = "reject"
    ACTION_COMPLETE = "complete"
    ACTION_VERIFY_VALID = "verify_valid"
    ACTION_VERIFY_INVALID = "verify_invalid"
    ACTION_IN = "in"
    ACTION_OUT = "out"

    ACTION_CHOICES = (
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_SUBMIT, "Submit"),
        (ACTION_CONFIRM, "Confirm"),
        (ACTION_ACCEPT, "Accept"),
        (ACTION_REJECT, "Reject"),
        (ACTION_COMPLETE, "Complete"),
        (ACTION_VERIFY_VALID, "Verify Valid"),
        (ACTION_VERIFY_INVALID, "Verify Invalid"),
        (ACTION_IN, "In"),
        (ACTION_OUT, "Out"),
    )

    request = models.ForeignKey(
        AccessRequest,
        on_delete=models.CASCADE,
        related_name="history_entries",
        verbose_name="Access Request",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Actor",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    status = models.CharField(max_length=20, choices=AccessRequest.STATUS_CHOICES, verbose_name="Status")
    time = models.DateTimeField(auto_now_add=True, verbose_name="Time")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        ordering = ("-time", "-pk")
        verbose_name = "Access Request History"
        verbose_name_plural = "Access Request History"

    def __str__(self):
        return f"{self.get_action_display()} - {self.get_status_display()}"

    @property
    def action_label(self):
        return label_for(ACCESS_REQUEST_HISTORY_ACTION_LABELS, self.action)

    @property
    def status_label(self):
        return label_for(ACCESS_REQUEST_STATUS_LABELS, self.status)

    @classmethod
    def record(cls, *, request, actor=None, action, status, description=""):
        return cls.objects.create(
            request=request,
            actor=actor if getattr(actor, "is_authenticated", True) else None,
            action=action,
            status=status,
            description=normalize_text(description),
        )


def get_access_request_creator(access_request):
    """Lấy người tạo phiếu, ưu tiên field mới và fallback về ObjectChange legacy."""
    if getattr(access_request, "created_by_id", None):
        return access_request.created_by

    content_type = ContentType.objects.get_for_model(access_request)
    return (
        ObjectChange.objects.filter(
            changed_object_type=content_type,
            changed_object_id=access_request.pk,
            action=ObjectChangeActionChoices.ACTION_CREATE,
            user__isnull=False,
        )
        .select_related("user")
        .order_by("time")
        .first()
    )


def notify_access_request_creator(access_request, *, subject, message):
    creator = get_access_request_creator(access_request)
    creator = getattr(creator, "user", creator)
    email = getattr(creator, "email", "")
    if not email:
        return 0

    return send_mail(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        [email],
        fail_silently=True,
    )


@receiver(pre_delete, sender=AccessRequestPerson)
def delete_access_request_person_files(sender, instance, **kwargs):
    """Dọn file đính kèm khi xóa đối tượng vào ra bằng bất kỳ đường nào."""
    delete_uploaded_files(instance, model_name="accessrequestperson")


def notify_access_request_admins(access_request, submitted_by=None):
    recipients = list(
        get_user_model()
        .objects.filter(
            groups__name="Admin",
            is_active=True,
            email__gt="",
        )
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients:
        return 0

    subject = f"Phiếu yêu cầu đã gửi: {access_request.name}"
    actor_name = getattr(submitted_by, "get_username", lambda: "")() or "Guest"
    message = (
        f"{actor_name} đã gửi phiếu yêu cầu {access_request.name}.\n"
        f"Ngày dự kiến: {access_request.expected_date}\n"
        f"Địa điểm: {access_request.site or '-'}\n"
        f"Trạng thái: {access_request.status_label}"
    )
    return send_mail(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipients,
        fail_silently=True,
    )
