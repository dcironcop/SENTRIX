from flask import Blueprint, render_template, request, send_file, jsonify, current_app, url_for
from flask_login import login_required, current_user
import os

from background_jobs import get_job, start_job
from services.export_service import build_export_bytes, build_export_file

export_bp = Blueprint("export", __name__, url_prefix="/export")


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
        async_mode = request.form.get("async") == "1"

        if not selected_fields:
            return render_template("export/index.html", fields=fields, error="Chưa chọn trường export")

        field_labels = {field[0]: field[1] for field in fields}

        if async_mode:
            output_dir = current_app.config.get("EXPORT_FOLDER", "exports")
            job_id = start_job(
                build_export_file,
                selected_fields,
                field_labels,
                output_dir,
                current_user.id,
            )
            return jsonify({"job_id": job_id, "status_url": url_for("export.export_status", job_id=job_id)})

        output = build_export_bytes(selected_fields, field_labels, user_id=current_user.id)
        return send_file(output, download_name="export_m2.xlsx", as_attachment=True)

    return render_template("export/index.html", fields=fields)


@export_bp.route("/status/<job_id>")
@login_required
def export_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@export_bp.route("/download/<job_id>")
@login_required
def download_export(job_id):
    job = get_job(job_id)
    if not job or job.get("status") != "finished":
        return jsonify({"error": "Export not ready"}), 404

    file_path = job.get("result")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, download_name=os.path.basename(file_path), as_attachment=True)
