import csv
from io import BytesIO

from django.http import HttpResponse
from django.urls import reverse

from .contracts import (
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


class SmartLockExportService:
    excel_filename = "netbox_smartlocks.xlsx"
    core_csv_filename = "netbox_smartlocks.csv"

    @classmethod
    def build_control_urls(cls, request):
        excel_params = request.GET.copy()
        excel_params.pop("export", None)
        excel_params[SMARTLOCK_CUSTOM_EXPORT_PARAM] = SMARTLOCK_EXPORT_EXCEL_REPORT

        return {
            "excel_export_url": f"{request.path}?{excel_params.urlencode()}",
            "import_url": reverse("plugins:netbox_smartlock:smartlock_import"),
        }

    @classmethod
    def is_custom_export_request(cls, request):
        return request.GET.get(SMARTLOCK_CUSTOM_EXPORT_PARAM) == SMARTLOCK_EXPORT_EXCEL_REPORT

    @classmethod
    def dispatch_custom_export(cls, request, *, view, queryset):
        """Chỉ xử lý export Excel bổ sung; export CSV lõi vẫn đi theo cơ chế NetBox."""
        export_type = request.GET.get(SMARTLOCK_CUSTOM_EXPORT_PARAM)

        if export_type == SMARTLOCK_EXPORT_EXCEL_REPORT:
            actions = view.get_permitted_actions(request.user)
            has_table_actions = any(action.multi for action in actions)
            table = view.get_table(queryset, request, has_table_actions)
            selected_columns = [name for name, _ in table.selected_columns]
            return cls.export_excel_report(table, selected_columns)

        return None

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
        worksheet.title = "Khóa thông minh"

        for row_index, row in enumerate(rows, start=1):
            worksheet.append(["" if value is None else str(value) for value in row])
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


class AccessRequestExportService:
    excel_filename = "netbox_access_requests.xlsx"

    @classmethod
    def build_control_urls(cls, request):
        excel_params = request.GET.copy()
        excel_params.pop("export", None)
        excel_params["accessrequest_export"] = "excel_report"

        return {
            "excel_export_url": f"{request.path}?{excel_params.urlencode()}",
        }

    @staticmethod
    def is_custom_export_request(request):
        return request.GET.get("accessrequest_export") == "excel_report"

    @classmethod
    def dispatch_custom_export(cls, request, *, view, queryset):
        if not cls.is_custom_export_request(request):
            return None

        actions = view.get_permitted_actions(request.user)
        has_table_actions = any(action.multi for action in actions)
        table = view.get_table(queryset, request, has_table_actions)
        selected_columns = [name for name, _ in table.selected_columns]
        return cls.export_excel_report(table, selected_columns)

    @classmethod
    def export_excel_report(cls, table, columns=None):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        # Queryset truyền vào đã được scope theo quyền, nên export không tự mở rộng dữ liệu.
        exclude_columns = cls._excluded_excel_columns(table, columns=columns)
        rows = list(table.as_values(exclude_columns=exclude_columns))

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Phiếu yêu cầu"

        for row_index, row in enumerate(rows, start=1):
            worksheet.append(["" if value is None else str(value) for value in row])
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
