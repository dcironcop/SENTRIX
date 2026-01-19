from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required
from models import Camera
from security_utils import log_audit
import pandas as pd
import json
import csv
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

export_bp = Blueprint("export", __name__, url_prefix="/export")


# =========================
# Helper
# =========================

def json_to_text(val):
    if not val:
        return ""
    try:
        data = json.loads(val)
        if isinstance(data, list):
            return ", ".join(data)
        return str(data)
    except:
        return str(val)


# =========================
# Routes
# =========================

@export_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    fields = [
        # Nhóm A
        ("owner_name", "Chủ sở hữu"),
        ("organization_name", "Đơn vị quản lý"),
        ("address_street", "Địa chỉ"),
        ("ward", "Phường/Xã"),
        ("province", "Tỉnh/Thành phố"),
        ("phone", "Điện thoại"),
        ("camera_index", "Thứ tự camera"),
        ("system_type", "Hệ thống camera"),

        # Nhóm B
        ("monitoring_modes", "Chế độ giám sát"),
        ("storage_types", "Lưu trữ"),
        ("retention_days", "Thời gian lưu trữ (ngày)"),

        # Nhóm C
        ("manufacturer", "Hãng sản xuất"),
        ("camera_types", "Chủng loại camera"),
        ("form_factors", "Kiểu dáng"),
        ("network_types", "Kết nối mạng"),

        # Nhóm D
        ("install_areas", "Khu vực lắp đặt"),
        ("latlon", "Tọa độ"),

        # Nhóm E
        ("login_user", "User"),
        ("login_domain", "Tên miền"),
        ("static_ip", "IP tĩnh"),
        ("ip_port", "IP:Port"),
        ("dvr_model", "Đầu ghi"),
        ("camera_model", "Model"),

        # Nhóm F
        ("resolution", "Độ phân giải"),
        ("bandwidth", "Băng thông"),
        ("serial_number", "Serial Number"),
        ("verification_code", "Mã xác minh"),
        ("category", "Phân loại"),
        ("sharing_scope", "Chia sẻ"),
    ]

    if request.method == "POST":
        selected_fields = request.form.getlist("fields")

        if not selected_fields:
            return render_template("export/index.html", fields=fields, error="Chưa chọn trường export")

        cameras = Camera.query.all()
        rows = []

        # Map field names to Vietnamese labels
        field_labels = {field[0]: field[1] for field in fields}
        
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
                
                # Use Vietnamese label as column name
                label = field_labels.get(field, field)
                row[label] = value if value is not None else ""

            rows.append(row)

        df = pd.DataFrame(rows)

        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(
            output,
            download_name="export_m2.xlsx",
            as_attachment=True
        )

    return render_template("export/index.html", fields=fields)
