import io
import json
import os
from datetime import datetime

import pandas as pd

from models import Camera
from security_utils import log_audit


def json_to_text(val):
    if not val:
        return ""
    try:
        data = json.loads(val)
        if isinstance(data, list):
            return ", ".join(data)
        return str(data)
    except Exception:  # noqa: BLE001
        return str(val)


def build_export_bytes(selected_fields, field_labels, user_id=None):
    cameras = Camera.query.all()
    rows = []

    for cam in cameras:
        row = {}
        for field in selected_fields:
            value = getattr(cam, field, "")

            if field in [
                "monitoring_modes",
                "storage_types",
                "camera_types",
                "form_factors",
                "network_types",
                "install_areas",
            ]:
                value = json_to_text(value)

            if field == "sharing_scope":
                value = "Có" if value else "Không"

            label = field_labels.get(field, field)
            row[label] = value if value is not None else ""

        rows.append(row)

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    if user_id:
        log_audit(
            "export",
            "camera",
            None,
            {"fields": selected_fields, "row_count": len(rows)},
        )

    return output


def build_export_file(selected_fields, field_labels, output_dir, user_id=None):
    output = build_export_bytes(selected_fields, field_labels, user_id=user_id)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"export_m2_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "wb") as handle:
        handle.write(output.getvalue())
    return file_path
