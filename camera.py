from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Camera
from sqlalchemy import func
from import_data import convert_latlon
from services.camera_service import CameraService
import pandas as pd
import io
import json

camera_bp = Blueprint("camera", __name__, url_prefix="/camera")


@camera_bp.route("/", methods=["GET", "POST"])
@login_required
def search():
    from flask import current_app
    
    # Nếu là POST, redirect sang GET với query params để hỗ trợ pagination
    if request.method == "POST":
        params = []
        f = request.form
        
        # Thêm các filter vào query params
        for key in ["owner_name", "organization_name", "address_street", "ward", 
                    "province", "phone", "manufacturer", "latlon", "static_ip"]:
            val = f.get(key)
            if val:
                params.append(f"{key}={val}")
        
        # Thêm các filter dạng list
        for key in ["monitoring_modes", "storage_types", "camera_types", 
                    "form_factors", "network_types", "install_areas"]:
            for val in f.getlist(key):
                if val:
                    params.append(f"{key}={val}")
        
        query_string = "&".join(params)
        return redirect(url_for("camera.search") + ("?" + query_string if query_string else ""))
    
    # GET request - xử lý search và pagination
    # Build filters dictionary
    filters = {}
    has_filters = False
    
    # ===== BASIC =====
    for field in ["owner_name", "organization_name", "address_street", "ward", 
                  "province", "phone", "manufacturer", "latlon", "static_ip"]:
        value = request.args.get(field)
        if value:
            filters[field] = value
            has_filters = True
    
    # ===== ADVANCED =====
    for field in ["monitoring_modes", "storage_types", "camera_types", 
                  "form_factors", "network_types", "install_areas"]:
        values = request.args.getlist(field)
        if values:
            filters[field] = values
            has_filters = True
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('CAMERAS_PER_PAGE', 50)
    
    # Use service layer for search
    if has_filters:
        results, total_results, pagination = CameraService.search_cameras(
            filters, page=page, per_page=per_page
        )
    else:
        pagination = None
        results = None
        total_results = 0
    
    # Lưu các filter để hiển thị lại trong form
    display_filters = {
        "owner_name": filters.get("owner_name", ""),
        "organization_name": filters.get("organization_name", ""),
        "address_street": filters.get("address_street", ""),
        "ward": filters.get("ward", ""),
        "province": filters.get("province", ""),
        "phone": filters.get("phone", ""),
        "manufacturer": filters.get("manufacturer", ""),
        "latlon": filters.get("latlon", ""),
        "static_ip": filters.get("static_ip", ""),
        "monitoring_modes": filters.get("monitoring_modes", []),
        "storage_types": filters.get("storage_types", []),
        "camera_types": filters.get("camera_types", []),
        "form_factors": filters.get("form_factors", []),
        "network_types": filters.get("network_types", []),
        "install_areas": filters.get("install_areas", []),
    }
    
    # Helper function để build pagination URL
    def build_pagination_url(page_num):
        """Build URL với tất cả query params hiện tại, chỉ thay đổi page"""
        args = request.args.copy()
        args['page'] = page_num
        return url_for('camera.search', **args)
    
    # Helper function để build URL với tất cả query params hiện tại (cho return_url)
    def build_current_search_url():
        """Build URL với tất cả query params hiện tại, giữ nguyên page"""
        args = request.args.copy()
        return url_for('camera.search', **args)
    
    return render_template(
        "camera/search.html", 
        results=results,
        pagination=pagination,
        total_results=total_results,
        filters=display_filters,
        build_pagination_url=build_pagination_url,
        build_current_search_url=build_current_search_url
    )


@camera_bp.route("/<int:camera_id>")
@login_required
def detail(camera_id):
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        abort(404)
    # Format JSON fields để hiển thị đẹp hơn
    camera.monitoring_modes_list = camera.get_json("monitoring_modes")
    camera.storage_types_list = camera.get_json("storage_types")
    camera.camera_types_list = camera.get_json("camera_types")
    camera.form_factors_list = camera.get_json("form_factors")
    camera.network_types_list = camera.get_json("network_types")
    camera.install_areas_list = camera.get_json("install_areas")
    
    # Lấy thông tin return URL từ query string
    return_url = request.args.get('return_url')
    ward = request.args.get('ward')
    
    # Nếu không có return_url, ưu tiên sử dụng referrer (trang trước đó)
    if not return_url:
        referrer = request.referrer
        # Chỉ sử dụng referrer nếu nó là từ cùng domain và không phải là detail page khác
        if referrer and request.host in referrer and '/camera/' not in referrer:
            return_url = referrer
        elif ward:
            return_url = url_for('camera.edit_list', ward=ward)
        else:
            return_url = url_for('camera.search')
    
    # Nếu không có ward từ query string, dùng ward của camera (nếu có)
    if not ward and camera.ward:
        ward = camera.ward
    
    return render_template("camera/detail2.html", camera=camera, return_url=return_url, ward=ward or '')


@camera_bp.route("/export", methods=["POST"])
@login_required
def export():
    ids = request.form.getlist("camera_ids")
    # Nếu không có camera nào được chọn, lấy tất cả camera từ kết quả tìm kiếm
    if not ids:
        all_ids = request.form.getlist("all_camera_ids")
        if all_ids:
            ids = all_ids
        else:
            flash("⚠️ Vui lòng chọn ít nhất một camera để xuất dữ liệu", "warning")
            return redirect(url_for("camera.search"))
    
    selected_fields = request.form.getlist("export_fields")
    
    if not selected_fields:
        flash("⚠️ Vui lòng chọn ít nhất một trường để xuất", "warning")
        return redirect(url_for("camera.search"))
    
    cameras = CameraService.get_cameras_by_ids(ids)

    def format_json_field(value):
        """Format JSON field để hiển thị dạng text"""
        if not value:
            return ""
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return ", ".join(data)
            return str(data)
        except (ValueError, TypeError, json.JSONDecodeError):
            # JSON parsing failed - return original value as string
            return str(value)

    # Mapping field codes to labels and formatters
    field_map = {
        "system_type": ("Hệ thống camera", lambda c: c.system_type or ""),
        "owner_name": ("Họ tên / Định danh", lambda c: c.owner_name or ""),
        "organization_name": ("Cơ quan / Tổ chức", lambda c: c.organization_name or ""),
        "phone": ("Điện thoại", lambda c: c.phone or ""),
        "address_street": ("Địa chỉ", lambda c: c.address_street or ""),
        "ward": ("Phường/Xã", lambda c: c.ward or ""),
        "province": ("Tỉnh/TP", lambda c: c.province or ""),
        "camera_index": ("Mã camera", lambda c: c.camera_index or ""),
        "monitoring_modes": ("Chế độ giám sát", lambda c: format_json_field(c.monitoring_modes)),
        "storage_types": ("Lưu trữ", lambda c: format_json_field(c.storage_types)),
        "retention_days": ("Thời gian lưu trữ (ngày)", lambda c: c.retention_days or ""),
        "manufacturer": ("Hãng sản xuất", lambda c: c.manufacturer or ""),
        "camera_types": ("Chủng loại camera", lambda c: format_json_field(c.camera_types)),
        "form_factors": ("Kiểu dáng", lambda c: format_json_field(c.form_factors)),
        "network_types": ("Kết nối mạng", lambda c: format_json_field(c.network_types)),
        "resolution": ("Độ phân giải", lambda c: c.resolution or ""),
        "bandwidth": ("Băng thông", lambda c: c.bandwidth or ""),
        "serial_number": ("S/N", lambda c: c.serial_number or ""),
        "install_areas": ("Khu vực lắp đặt", lambda c: format_json_field(c.install_areas)),
        "latlon": ("Tọa độ", lambda c: c.latlon or ""),
        "login_user": ("User đăng nhập", lambda c: c.login_user or ""),
        "login_domain": ("Tên miền / DDNS", lambda c: c.login_domain or ""),
        "static_ip": ("IP tĩnh", lambda c: c.static_ip or ""),
        "ip_port": ("Cổng (port)", lambda c: c.ip_port or ""),
        "dvr_model": ("Đầu ghi (DVR)", lambda c: c.dvr_model or ""),
        "camera_model": ("Mẫu camera", lambda c: c.camera_model or ""),
        "verification_code": ("Mã xác minh", lambda c: c.verification_code or ""),
        "category": ("Phân loại", lambda c: c.category or ""),
        "sharing_scope": ("Chia sẻ", lambda c: "Có" if c.sharing_scope else "Không"),
    }

    rows = []
    for c in cameras:
        row = {}
        for field_code in selected_fields:
            if field_code in field_map:
                label, formatter = field_map[field_code]
                row[label] = formatter(c)
        rows.append(row)

    df = pd.DataFrame(rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Kết quả tra cứu")

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="ket_qua_tra_cuu_M2.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@camera_bp.route("/compare")
@login_required
def compare():
    """Trang so sánh nhiều camera side-by-side"""
    ids_str = request.args.get('ids', '')
    if not ids_str:
        flash("⚠️ Vui lòng chọn ít nhất 2 camera để so sánh", "warning")
        return redirect(url_for("camera.search"))
    
    try:
        ids = [int(id.strip()) for id in ids_str.split(',') if id.strip()]
        if len(ids) < 2:
            flash("⚠️ Vui lòng chọn ít nhất 2 camera để so sánh", "warning")
            return redirect(url_for("camera.search"))
        if len(ids) > 5:
            flash("⚠️ Chỉ có thể so sánh tối đa 5 camera cùng lúc", "warning")
            return redirect(url_for("camera.search"))
    except ValueError:
        flash("⚠️ ID camera không hợp lệ", "error")
        return redirect(url_for("camera.search"))
    
    cameras = CameraService.get_cameras_by_ids(ids)
    if len(cameras) != len(ids):
        flash("⚠️ Một số camera không tồn tại", "warning")
    
    return render_template("camera/compare.html", cameras=cameras)


@camera_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    # Chỉ admin mới được tạo mới
    if not current_user.is_admin():
        abort(403)

    if request.method == "POST":
        f = request.form

        def list_field(name):
            return [v for v in f.getlist(name) if v]

        cam = Camera(
            # Nhóm A
            owner_name=f.get("owner_name"),
            organization_name=f.get("organization_name"),
            address_street=f.get("address_street"),
            ward=f.get("ward"),
            province=f.get("province"),
            phone=f.get("phone"),
            camera_index=f.get("camera_index") or None,
            system_type=f.get("system_type"),
            # Nhóm B
            retention_days=f.get("retention_days") or None,
            # Nhóm C
            manufacturer=f.get("manufacturer"),
            static_ip=f.get("static_ip"),
            ip_port=f.get("ip_port"),
            dvr_model=f.get("dvr_model"),
            camera_model=f.get("camera_model"),
            # Nhóm D
            latlon=f.get("latlon"),
            # Nhóm E
            login_user=f.get("login_user"),
            login_password=f.get("login_password"),
            login_domain=f.get("login_domain"),
            # Nhóm F
            resolution=f.get("resolution"),
            bandwidth=f.get("bandwidth"),
            serial_number=f.get("serial_number"),
            verification_code=f.get("verification_code"),
            category=f.get("category"),
            sharing_scope=bool(f.get("sharing_scope")),
        )

        # Prepare JSON fields
        json_fields = {
            "monitoring_modes": list_field("monitoring_modes"),
            "storage_types": list_field("storage_types"),
            "camera_types": list_field("camera_types"),
            "form_factors": list_field("form_factors"),
            "network_types": list_field("network_types"),
            "install_areas": list_field("install_areas")
        }
        
        # Use service layer to create camera
        cam = CameraService.create_camera(
            camera_data={
                "owner_name": f.get("owner_name"),
                "organization_name": f.get("organization_name"),
                "address_street": f.get("address_street"),
                "ward": f.get("ward"),
                "province": f.get("province"),
                "phone": f.get("phone"),
                "camera_index": f.get("camera_index") or None,
                "system_type": f.get("system_type"),
                "retention_days": f.get("retention_days") or None,
                "manufacturer": f.get("manufacturer"),
                "static_ip": f.get("static_ip"),
                "ip_port": f.get("ip_port"),
                "dvr_model": f.get("dvr_model"),
                "camera_model": f.get("camera_model"),
                "latlon": f.get("latlon"),
                "login_user": f.get("login_user"),
                "login_password": f.get("login_password"),
                "login_domain": f.get("login_domain"),
                "resolution": f.get("resolution"),
                "bandwidth": f.get("bandwidth"),
                "serial_number": f.get("serial_number"),
                "verification_code": f.get("verification_code"),
                "category": f.get("category"),
                "sharing_scope": bool(f.get("sharing_scope")),
            },
            json_fields=json_fields,
            user_id=current_user.id
        )
        
        flash("✅ Đã tạo camera mới", "success")
        # Redirect đến detail với return_url về search
        return redirect(url_for("camera.detail", camera_id=cam.id, return_url=url_for("camera.search")))

    return render_template("camera/create.html")


@camera_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit_list():
    """Trang chọn địa bàn và hiển thị danh sách camera để chỉnh sửa/xóa"""
    # Chỉ admin mới được chỉnh sửa
    if not current_user.is_admin():
        abort(403)
    
    # Use service layer to get wards
    wards = CameraService.get_wards_with_counts()
    
    selected_ward = request.args.get('ward', '')
    cameras = []
    
    if selected_ward:
        cameras = CameraService.get_cameras_by_ward(selected_ward)
    
    return render_template(
        "camera/edit.html",
        wards=wards,
        selected_ward=selected_ward,
        cameras=cameras
    )


@camera_bp.route("/edit/<int:camera_id>", methods=["GET", "POST"])
@login_required
def edit(camera_id):
    """Form chỉnh sửa camera"""
    # Chỉ admin mới được chỉnh sửa
    if not current_user.is_admin():
        abort(403)
    
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        abort(404)
    
    # Lấy return_url từ query string hoặc referrer
    return_url = request.args.get('return_url')
    if not return_url:
        referrer = request.referrer
        # Chỉ sử dụng referrer nếu nó là từ cùng domain và không phải là edit page
        if referrer and request.host in referrer and '/camera/edit/' not in referrer:
            return_url = referrer
        else:
            # Mặc định quay về detail page với ward
            return_url = url_for('camera.detail', camera_id=camera_id, ward=camera.ward or '')
    
    if request.method == "POST":
        f = request.form

        def list_field(name):
            return [v for v in f.getlist(name) if v]

        # Cập nhật tất cả các trường
        camera.owner_name = f.get("owner_name")
        camera.organization_name = f.get("organization_name")
        camera.address_street = f.get("address_street")
        camera.ward = f.get("ward")
        camera.province = f.get("province")
        camera.phone = f.get("phone")
        # Xử lý camera_index và retention_days (có thể là số hoặc string)
        camera_index_val = f.get("camera_index")
        if camera_index_val:
            try:
                camera.camera_index = int(camera_index_val)
            except (ValueError, TypeError):
                # Nếu không phải số, thử extract number
                from parse_m2 import extract_number
                extracted = extract_number(camera_index_val)
                camera.camera_index = extracted if extracted is not None else None
        else:
            camera.camera_index = None
            
        camera.system_type = f.get("system_type")
        
        # Xử lý retention_days tương tự
        retention_val = f.get("retention_days")
        if retention_val:
            try:
                camera.retention_days = int(retention_val)
            except (ValueError, TypeError):
                from parse_m2 import extract_number
                extracted = extract_number(retention_val)
                camera.retention_days = extracted if extracted is not None else None
        else:
            camera.retention_days = None
        
        camera.manufacturer = f.get("manufacturer")
        camera.static_ip = f.get("static_ip")
        camera.ip_port = f.get("ip_port")
        camera.dvr_model = f.get("dvr_model")
        camera.camera_model = f.get("camera_model")
        
        # Xử lý và chuyển đổi tọa độ
        latlon_value = f.get("latlon")
        if latlon_value:
            converted_latlon = convert_latlon(latlon_value)
            if converted_latlon:
                camera.latlon = converted_latlon
            else:
                flash(f"⚠️ Tọa độ không hợp lệ: {latlon_value}. Đã lưu giá trị gốc.", "warning")
                camera.latlon = latlon_value
        else:
            camera.latlon = None
        
        camera.login_user = f.get("login_user")
        # Chỉ cập nhật password nếu có giá trị mới
        if f.get("login_password"):
            camera.login_password = f.get("login_password")
        camera.login_domain = f.get("login_domain")
        
        camera.resolution = f.get("resolution")
        camera.bandwidth = f.get("bandwidth")
        camera.serial_number = f.get("serial_number")
        camera.verification_code = f.get("verification_code")
        camera.category = f.get("category")
        camera.sharing_scope = bool(f.get("sharing_scope"))

        # Prepare JSON fields
        json_fields = {
            "monitoring_modes": list_field("monitoring_modes"),
            "storage_types": list_field("storage_types"),
            "camera_types": list_field("camera_types"),
            "form_factors": list_field("form_factors"),
            "network_types": list_field("network_types"),
            "install_areas": list_field("install_areas")
        }
        
        # Use service layer to update camera
        camera_data = {
            "owner_name": f.get("owner_name"),
            "organization_name": f.get("organization_name"),
            "address_street": f.get("address_street"),
            "ward": f.get("ward"),
            "province": f.get("province"),
            "phone": f.get("phone"),
            "system_type": f.get("system_type"),
            "manufacturer": f.get("manufacturer"),
            "static_ip": f.get("static_ip"),
            "ip_port": f.get("ip_port"),
            "dvr_model": f.get("dvr_model"),
            "camera_model": f.get("camera_model"),
            "login_user": f.get("login_user"),
            "login_domain": f.get("login_domain"),
            "resolution": f.get("resolution"),
            "bandwidth": f.get("bandwidth"),
            "serial_number": f.get("serial_number"),
            "verification_code": f.get("verification_code"),
            "category": f.get("category"),
            "sharing_scope": bool(f.get("sharing_scope")),
        }
        
        # Handle camera_index
        camera_index_val = f.get("camera_index")
        if camera_index_val:
            try:
                camera_data["camera_index"] = int(camera_index_val)
            except (ValueError, TypeError):
                from parse_m2 import extract_number
                extracted = extract_number(camera_index_val)
                camera_data["camera_index"] = extracted if extracted is not None else None
        else:
            camera_data["camera_index"] = None
        
        # Handle retention_days
        retention_val = f.get("retention_days")
        if retention_val:
            try:
                camera_data["retention_days"] = int(retention_val)
            except (ValueError, TypeError):
                from parse_m2 import extract_number
                extracted = extract_number(retention_val)
                camera_data["retention_days"] = extracted if extracted is not None else None
        else:
            camera_data["retention_days"] = None
        
        # Handle latlon conversion
        latlon_value = f.get("latlon")
        if latlon_value:
            converted_latlon = convert_latlon(latlon_value)
            if converted_latlon:
                camera_data["latlon"] = converted_latlon
            else:
                flash(f"⚠️ Tọa độ không hợp lệ: {latlon_value}. Đã lưu giá trị gốc.", "warning")
                camera_data["latlon"] = latlon_value
        else:
            camera_data["latlon"] = None
        
        # Handle password (only update if provided)
        if f.get("login_password"):
            camera_data["login_password"] = f.get("login_password")
        
        updated_camera = CameraService.update_camera(
            camera_id=camera_id,
            camera_data=camera_data,
            json_fields=json_fields,
            user_id=current_user.id
        )
        
        if not updated_camera:
            abort(404)
        
        flash("✅ Đã cập nhật thông tin camera", "success")
        # Quay về return_url nếu có, nếu không thì về edit_list
        if return_url:
            return redirect(return_url)
        return redirect(url_for("camera.edit_list", ward=camera.ward))

    return render_template("camera/edit_form.html", camera=camera, return_url=return_url)


@camera_bp.route("/delete/<int:camera_id>", methods=["POST"])
@login_required
def delete(camera_id):
    """Xóa camera"""
    # Chỉ admin mới được xóa
    if not current_user.is_admin():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Không có quyền xóa'}), 403
        abort(403)
    
    # Get camera to retrieve ward before deletion
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Camera không tồn tại'}), 404
        abort(404)
    
    ward = camera.ward or ''  # Lưu ward để redirect về (có thể None)
    
    # Use service layer to delete camera
    success = CameraService.delete_camera(camera_id, user_id=current_user.id)
    
    if not success:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Không thể xóa camera'}), 400
        abort(404)
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Đã xóa camera thành công'})
    
    flash("✅ Đã xóa camera", "success")
    
    # Nếu có ward, redirect về danh sách camera của ward đó, nếu không thì về trang chọn ward
    if ward:
        return redirect(url_for("camera.edit_list", ward=ward))
    else:
        return redirect(url_for("camera.edit_list"))


@camera_bp.route("/<int:camera_id>/stream")
@login_required
def stream_view(camera_id):
    """Trang xem trực tiếp camera"""
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        abort(404)
    
    # Lấy stream info
    stream_info_data = _get_stream_info(camera)
    
    if not stream_info_data.get("available"):
        flash("⚠️ Camera này không thể xem trực tiếp. " + stream_info_data.get("error", ""), "warning")
        return redirect(url_for("camera.detail", camera_id=camera_id))
    
    # Get return URL
    return_url = request.args.get('return_url') or request.referrer
    if not return_url or return_url == request.url:
        return_url = url_for("camera.detail", camera_id=camera_id)
    
    return render_template(
        "camera/stream.html",
        camera=camera,
        stream_data=stream_info_data,
        stream_data_json=json.dumps(stream_info_data),
        return_url=return_url
    )


@camera_bp.route("/<int:camera_id>/stream-info", methods=["GET"])
@login_required
def stream_info(camera_id):
    """API trả về thông tin streaming của camera"""
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        abort(404)
    
    stream_info_data = _get_stream_info(camera)
    return jsonify(stream_info_data)


def _get_stream_info(camera):
    """Helper function để tạo stream info"""
    # Kiểm tra xem camera có đủ thông tin để stream không
    has_connection_info = bool(camera.static_ip or camera.login_domain)
    has_credentials = bool(camera.login_user and camera.login_password)
    
    if not has_connection_info:
        return {
            "available": False,
            "error": "Camera chưa có thông tin kết nối (IP/Domain)"
        }
    
    # Xác định địa chỉ camera
    camera_address = camera.login_domain if camera.login_domain else camera.static_ip
    camera_port = camera.ip_port if camera.ip_port else "554"  # RTSP default port
    http_port = camera_port if camera_port != "554" else "80"
    
    # Tạo các URL streaming có thể
    stream_urls = {}
    manufacturer_lower = (camera.manufacturer or "").lower()
    
    if has_credentials:
        # RTSP URL (phổ biến nhất cho IP camera)
        rtsp_paths = {
            "hikvision": "/Streaming/Channels/101",
            "hik": "/Streaming/Channels/101",
            "dahua": "/cam/realmonitor?channel=1&subtype=0",
            "tp-link": "/stream1",
            "tplink": "/stream1",
            "axis": "/axis-media/media.amp",
            "uniview": "/Streaming/Channels/101",
            "hanwha": "/Streaming/Channels/101",
            "samsung": "/Streaming/Channels/101"
        }
        
        rtsp_path = "/stream1"  # Default
        for key, path in rtsp_paths.items():
            if key in manufacturer_lower:
                rtsp_path = path
                break
        
        rtsp_url = f"rtsp://{camera.login_user}:{camera.login_password}@{camera_address}:{camera_port}{rtsp_path}"
        stream_urls["rtsp"] = rtsp_url
        
        # HTTP/MJPEG URL (nếu camera hỗ trợ)
        mjpeg_paths = {
            "hikvision": "/Streaming/channels/101/picture",
            "hik": "/Streaming/channels/101/picture",
            "dahua": "/cgi-bin/snapshot.cgi",
            "axis": "/axis-cgi/mjpg/video.cgi",
            "uniview": "/Streaming/channels/101/picture",
            "hanwha": "/Streaming/channels/101/picture"
        }
        
        mjpeg_path = "/video.cgi"  # Default
        for key, path in mjpeg_paths.items():
            if key in manufacturer_lower:
                mjpeg_path = path
                break
        
        http_url = f"http://{camera.login_user}:{camera.login_password}@{camera_address}:{http_port}{mjpeg_path}"
        stream_urls["http"] = http_url
        stream_urls["mjpeg"] = http_url
        
        # HLS URL (nếu có proxy server)
        # stream_urls["hls"] = f"/camera/{camera.id}/stream-hls"
    
    return {
        "available": True,
        "camera_id": camera.id,
        "camera_name": camera.owner_name or camera.organization_name or f"Camera #{camera.id}",
        "address": camera_address,
        "port": camera_port,
        "has_credentials": has_credentials,
        "stream_urls": stream_urls,
        "manufacturer": camera.manufacturer,
        "note": "RTSP streams cần được convert sang HLS/WebRTC để play trong browser. HTTP/MJPEG có thể play trực tiếp."
    }
