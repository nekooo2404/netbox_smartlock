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


def validate_file_size(value):
    """Kept for historical migrations that referenced the legacy attachment field."""
    max_size = 25 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError("Attached file must not exceed 25MB.")


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class AssetGroup(OrganizationalModel):
    """Asset grouping and device classification."""

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
    """Smart Lock device."""

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

    def get_absolute_url(self):
        return reverse("plugins:netbox_smartlock:smartlock", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        errors = {}

        if self.rack_face and not self.rack_id:
            errors["rack"] = "Select a Rack before selecting a rack face."

        sync_smartlock_hierarchy(self, errors=errors)

        if self.warranty_period is not None and not self.bought_date:
            errors["bought_date"] = "Purchase date is required when warranty period is set."

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
    """Guest request for entering a data center site."""

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
    def can_guest_edit(self):
        return self.status not in (self.STATUS_ACCEPTED, self.STATUS_COMPLETED)

    @property
    def can_guest_delete(self):
        return self.status not in (self.STATUS_ACCEPTED, self.STATUS_COMPLETED)

    @property
    def can_submit(self):
        if self.status not in (self.STATUS_DRAFT, self.STATUS_REJECTED):
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
            errors["site"] = "Selected Site must belong to the selected Region."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = normalize_text(self.name)
        self.reason = normalize_text(self.reason)
        self.full_clean()
        return super().save(*args, **kwargs)

    def submit(self, user=None, description=""):
        if not self.can_submit:
            raise ValidationError("An access request must have at least one person and be editable before it can be submitted.")

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
            raise ValidationError("Only submitted access requests can be confirmed by an admin.")

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
            raise ValidationError("Only confirmed access requests can be accepted.")
        if self.persons.filter(verify_status=AccessRequestPerson.VERIFY_INVALID).exists():
            raise ValidationError("Cannot accept an access request with invalid persons.")
        if self.persons.exclude(verify_status=AccessRequestPerson.VERIFY_VALID).exists():
            raise ValidationError("All persons must be verified valid before an access request can be accepted.")

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
            subject=f"Access request accepted: {self.name}",
            message=f"Access request {self.name} has been accepted.\nDescription: {description or '-'}",
        )
        return history

    def reject(self, user=None, description=""):
        if self.status != self.STATUS_CONFIRMED:
            raise ValidationError("Only confirmed access requests can be rejected.")
        if not normalize_text(description):
            raise ValidationError("A rejection reason is required.")

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
            subject=f"Access request rejected: {self.name}",
            message=f"Access request {self.name} has been rejected.\nReason: {description or '-'}",
        )
        return history

    def complete(self, user=None, description=""):
        if not self.can_admin_complete:
            raise ValidationError("Only accepted access requests can be completed.")

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
            subject=f"Access request completed: {self.name}",
            message=f"Access request {self.name} has been completed.",
        )
        return history

    def delete(self, *args, **kwargs):
        if not self.can_guest_delete:
            raise ValidationError("Accepted or completed access requests cannot be deleted by a guest user.")
        return super().delete(*args, **kwargs)


class AccessRequestPerson(NetBoxModel):
    """Person registered by a guest for an access request."""

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
    def can_guest_edit(self):
        if not self.request_id:
            return False

        request_queryset = AccessRequest.objects.filter(pk=self.request_id)
        if request_queryset.filter(status=AccessRequest.STATUS_REJECTED).exists():
            return True

        return bool(
            self.verify_status in (self.VERIFY_PENDING, self.VERIFY_INVALID)
            and request_queryset.exclude(
                status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
            ).exists()
        )

    @property
    def can_guest_delete(self):
        if not self.request_id:
            return False

        request_queryset = AccessRequest.objects.filter(pk=self.request_id)
        return bool(
            request_queryset.filter(status=AccessRequest.STATUS_REJECTED).exists()
            or request_queryset.filter(status=AccessRequest.STATUS_ACCEPTED).exists()
            or (
                self.verify_status in (self.VERIFY_PENDING, self.VERIFY_INVALID)
                and request_queryset.exclude(
                    status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
                ).exists()
            )
        )

    @property
    def can_admin_verify(self):
        return bool(
            self.request_id
            and AccessRequest.objects.filter(
                pk=self.request_id,
                status=AccessRequest.STATUS_CONFIRMED,
            ).exists()
        )

    @property
    def can_check_in(self):
        return bool(
            self.request_id
            and AccessRequest.objects.filter(
                pk=self.request_id,
                status=AccessRequest.STATUS_ACCEPTED,
            ).exists()
            and self.verify_status == self.VERIFY_VALID
            and self.access_status == self.ACCESS_OUT
        )

    @property
    def can_check_out(self):
        return bool(
            self.request_id
            and AccessRequest.objects.filter(
                pk=self.request_id,
                status=AccessRequest.STATUS_ACCEPTED,
            ).exists()
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
            errors["identity_code"] = "Identity code must contain exactly 12 digits."

        if self.phone and (
            len(self.phone) != 10
            or not self.phone.isdigit()
            or not self.phone.startswith(self.VIETNAMESE_MOBILE_PREFIXES)
        ):
            errors["phone"] = "Phone must be a valid 10-digit Vietnamese mobile phone number."

        if self.location_id and self.request_id and self.location.site_id != self.request.site_id:
            errors["location"] = "Selected Location must belong to the Access Request Site."

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
            raise ValidationError("This access request person cannot be deleted in the current workflow state.")
        return super().delete(*args, **kwargs)

    def mark_valid(self, user=None, description=""):
        if not self.can_admin_verify:
            raise ValidationError("Persons can only be verified after the access request is confirmed by an admin.")

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.verify_status = self.VERIFY_VALID
        self.save(update_fields=("verify_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_VERIFY_VALID,
            status=access_request.status,
            description=description or f"Marked {self.full_name} as valid.",
        )

    def mark_invalid(self, user=None, description=""):
        if not self.can_admin_verify:
            raise ValidationError("Persons can only be verified after the access request is confirmed by an admin.")

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.verify_status = self.VERIFY_INVALID
        self.save(update_fields=("verify_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_VERIFY_INVALID,
            status=access_request.status,
            description=description or f"Marked {self.full_name} as invalid.",
        )

    def check_in(self, user=None, description=""):
        if not self.can_check_in:
            raise ValidationError("Only valid persons in accepted access requests can be checked in from the Out state.")

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.access_status = self.ACCESS_IN
        self.save(update_fields=("access_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_CHECK_IN,
            status=access_request.status,
            description=description or f"Checked in {self.full_name}.",
        )

    def check_out(self, user=None, description=""):
        if not self.can_check_out:
            raise ValidationError("Only checked-in persons in accepted access requests can be checked out.")

        access_request = AccessRequest.objects.get(pk=self.request_id)
        self.access_status = self.ACCESS_OUT
        self.save(update_fields=("access_status", "last_updated"))
        return AccessRequestHistory.record(
            request=access_request,
            actor=user,
            action=AccessRequestHistory.ACTION_CHECK_OUT,
            status=access_request.status,
            description=description or f"Checked out {self.full_name}.",
        )


class AccessRequestHistory(models.Model):
    """Business history for access request workflow actions."""

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_SUBMIT = "submit"
    ACTION_CONFIRM = "confirm"
    ACTION_ACCEPT = "accept"
    ACTION_REJECT = "reject"
    ACTION_COMPLETE = "complete"
    ACTION_VERIFY_VALID = "verify_valid"
    ACTION_VERIFY_INVALID = "verify_invalid"
    ACTION_CHECK_IN = "check_in"
    ACTION_CHECK_OUT = "check_out"

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
        (ACTION_CHECK_IN, "Check In"),
        (ACTION_CHECK_OUT, "Check Out"),
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

    subject = f"Access request submitted: {access_request.name}"
    actor_name = getattr(submitted_by, "get_username", lambda: "")() or "Guest user"
    message = (
        f"{actor_name} submitted access request {access_request.name}.\n"
        f"Expected date: {access_request.expected_date}\n"
        f"Site: {access_request.site or '-'}\n"
        f"Status: {access_request.get_status_display()}"
    )
    return send_mail(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipients,
        fail_silently=True,
    )
