import csv
from html import unescape
from io import BytesIO

from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import strip_tags

from .contracts import (
    ASSETGROUP_CUSTOM_EXPORT_PARAM,
    ASSETGROUP_EXPORT_EXCEL_REPORT,
    DEVICE_ASSET_CUSTOM_EXPORT_PARAM,
    DEVICE_ASSET_EXPORT_EXCEL_REPORT,
    SMARTLOCK_CUSTOM_EXPORT_PARAM,
    SMARTLOCK_EXCEL_EXTRA_FIELDS,
    SMARTLOCK_EXPORT_EXCEL_REPORT,
    SMARTLOCK_IMPORT_FIELD_NAMES,
)
from .mapping import format_rack_lookup, get_warranty_state
from .ui import WARRANTY_STATE_LABELS, label_for
from .upload_files import file_names_by_object_ids


SMARTLOCK_EXCEL_EXTRA_LABELS = {
    "rack_lookup": "Tra cứu tủ rack",
    "warranty_state": "Trạng thái bảo hành",
    "uploaded_files": "File đính kèm",
}


def excel_cell_value(value):
    """Convert table-rendered values to plain text before writing XLSX cells."""
    if value is None:
        return ""
    return unescape(strip_tags(str(value))).strip()


class ExcelTableExportMixin:
    excel_filename = "netbox_export.xlsx"
    worksheet_title = "Export"
    custom_export_param = None
    custom_export_value = "excel_report"

    @classmethod
    def build_excel_export_url(cls, request):
        if not cls.custom_export_param:
            raise NotImplementedError("custom_export_param must be configured for Excel exports.")

        excel_params = request.GET.copy()
        excel_params.pop("export", None)
        excel_params[cls.custom_export_param] = cls.custom_export_value
        return f"{request.path}?{excel_params.urlencode()}"

    @classmethod
    def build_control_urls(cls, request):
        return {
            "excel_export_url": cls.build_excel_export_url(request),
        }

    @classmethod
    def is_custom_export_request(cls, request):
        return bool(cls.custom_export_param and request.GET.get(cls.custom_export_param) == cls.custom_export_value)

    @classmethod
    def dispatch_custom_export(cls, request, *, view, queryset):
        if not cls.is_custom_export_request(request):
            return None

        table, selected_columns = cls.build_export_table(request, view, queryset)
        return cls.export_excel_report(table, selected_columns)

    @staticmethod
    def build_export_table(request, view, queryset):
        actions = view.get_permitted_actions(request.user)
        has_table_actions = any(action.multi for action in actions)
        table = view.get_table(queryset, request, has_table_actions)
        selected_columns = [name for name, _ in table.selected_columns]
        return table, selected_columns

    @classmethod
    def export_excel_report(cls, table, columns=None):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        exclude_columns = cls._excluded_excel_columns(table, columns=columns)
        rows = list(table.as_values(exclude_columns=exclude_columns))

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = cls.worksheet_title

        for row_index, row in enumerate(rows, start=1):
            worksheet.append([excel_cell_value(value) for value in row])
            if row_index == 1:
                for cell in worksheet[row_index]:
                    cell.font = Font(bold=True)

        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 60)

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{cls.excel_filename}"'
        return response

    @staticmethod
    def _excluded_excel_columns(table, columns=None):
        exclude_columns = {"pk", "actions"}
        all_columns = [col_name for col_name, _ in table.selected_columns + table.available_columns]
        if columns:
            exclude_columns.update({col for col in all_columns if col not in columns})
        return exclude_columns


class AssetGroupExportService(ExcelTableExportMixin):
    excel_filename = "netbox_asset_groups.xlsx"
    worksheet_title = "Nhóm tài sản"
    custom_export_param = ASSETGROUP_CUSTOM_EXPORT_PARAM
    custom_export_value = ASSETGROUP_EXPORT_EXCEL_REPORT


class DeviceAssetExportService(ExcelTableExportMixin):
    excel_filename = "netbox_assets.xlsx"
    worksheet_title = "Tài sản"
    custom_export_param = DEVICE_ASSET_CUSTOM_EXPORT_PARAM
    custom_export_value = DEVICE_ASSET_EXPORT_EXCEL_REPORT


class SmartLockExportService(ExcelTableExportMixin):
    excel_filename = "netbox_smartlocks.xlsx"
    core_csv_filename = "netbox_smartlocks.csv"
    worksheet_title = "Khóa thông minh"
    custom_export_param = SMARTLOCK_CUSTOM_EXPORT_PARAM
    custom_export_value = SMARTLOCK_EXPORT_EXCEL_REPORT

    @classmethod
    def build_control_urls(cls, request):
        return {
            "excel_export_url": cls.build_excel_export_url(request),
            "import_url": reverse("plugins:netbox_smartlock:smartlock_import"),
        }

    @classmethod
    def export_core_csv(cls, queryset, *, filename=None, delimiter=None):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename or cls.core_csv_filename}"'

        writer = csv.DictWriter(
            response,
            fieldnames=SMARTLOCK_IMPORT_FIELD_NAMES,
            delimiter=delimiter or ",",
        )
        writer.writeheader()

        for obj in queryset:
            writer.writerow(cls.serialize_core_csv_row(obj))

        return response

    @staticmethod
    def serialize_core_csv_row(obj):
        return {
            "id": obj.pk,
            "name": obj.name,
            "code": obj.code,
            "asset_group": getattr(obj.asset_group, "slug", ""),
            "status": obj.status,
            "description": obj.description,
            "comments": obj.comments,
            "device_type": obj.device_type,
            "model": obj.model,
            "serial": obj.serial,
            "manufacturer": obj.manufacturer,
            "setup_date": obj.setup_date or "",
            "bought_date": obj.bought_date or "",
            "warranty_period": obj.warranty_period or "",
            "region": getattr(obj.region, "slug", ""),
            "site": getattr(obj.site, "slug", ""),
            "location": getattr(obj.location, "slug", ""),
            "rack_lookup": format_rack_lookup(obj.rack),
            "rack_face": obj.rack_face,
        }

    @classmethod
    def export_excel_report(cls, table, columns=None):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        # Excel report bổ sung các cột tính toán, còn CSV giữ đúng contract import/export.
        exclude_columns = cls._excluded_excel_columns(table, columns=columns)
        records = list(table.data)
        rows = list(table.as_values(exclude_columns=exclude_columns))
        object_ids = [record.pk for record in records]
        uploaded_file_names = file_names_by_object_ids(object_ids, model_name="smartlock")

        if rows:
            rows[0] = [*rows[0], *[SMARTLOCK_EXCEL_EXTRA_LABELS[field] for field in SMARTLOCK_EXCEL_EXTRA_FIELDS]]
            for index, record in enumerate(records, start=1):
                names = uploaded_file_names.get(record.pk, [])
                rows[index] = [
                    *rows[index],
                    format_rack_lookup(record.rack),
                    label_for(WARRANTY_STATE_LABELS, get_warranty_state(record.warranty_expiration_date)),
                    ", ".join(names),
                ]

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = cls.worksheet_title

        for row_index, row in enumerate(rows, start=1):
            worksheet.append([excel_cell_value(value) for value in row])
            if row_index == 1:
                for cell in worksheet[row_index]:
                    cell.font = Font(bold=True)

        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 60)

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{cls.excel_filename}"'
        return response


class AccessRequestExportService(ExcelTableExportMixin):
    excel_filename = "netbox_access_requests.xlsx"
    worksheet_title = "Phiếu yêu cầu"
    custom_export_param = "accessrequest_export"
