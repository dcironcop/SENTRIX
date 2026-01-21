from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import re
import pandas as pd

from background_jobs import get_job, start_job
from services.import_service import process_import

# Batch size for committing records (configurable)
DEFAULT_BATCH_SIZE = 100  # Commit every 100 records

import_bp = Blueprint("import", __name__, url_prefix="/import")


# =========================
# Helpers
# =========================

def allowed_file(filename, allowed_extensions=None):
    """Kiểm tra extension file có hợp lệ không"""
    if not filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if allowed_extensions is None:
        allowed_extensions = {'xls', 'xlsx'}  # Default
    return ext in allowed_extensions


def dms_to_decimal(dms_str):
    """
    Chuyển đổi tọa độ DMS (Degrees Minutes Seconds) sang decimal degrees.
    
    Algorithm:
    1. Extract direction (N/S/E/W)
    2. Parse degrees, minutes, seconds
    3. Convert to decimal: decimal = degrees + minutes/60 + seconds/3600
    4. Apply direction: S/W = negative
    
    Args:
        dms_str: String in DMS format (e.g., "19°47'26.5\"N")
        
    Returns:
        float: Decimal degrees (e.g., 19.790694) or None if invalid
        
    Example:
        >>> dms_to_decimal("19°47'26.5\"N")
        19.790694
        >>> dms_to_decimal("105°46'42.3\"E")
        105.778417
    """
    if not dms_str or pd.isna(dms_str):
        return None
    
    dms_str = str(dms_str).strip()
    
    # Tìm hướng (N/S/E/W) trước - có thể ở đầu hoặc cuối chuỗi
    direction_match = re.search(r'([NSEW])', dms_str, re.IGNORECASE)
    direction = direction_match.group(1).upper() if direction_match else ""
    
    # Loại bỏ hướng và các ký tự không cần thiết, chỉ giữ số
    # Pattern linh hoạt: degrees[°] minutes['] seconds["]
    # Hỗ trợ cả dấu °, ', " hoặc không có
    pattern = r"(\d+)[°\s]*(\d+)[\'\s]*([\d.]+)[\"\s]*"
    match = re.search(pattern, dms_str, re.IGNORECASE)
    
    if not match:
        return None
    
    try:
        degrees = float(match.group(1))
        minutes = float(match.group(2))
        seconds = float(match.group(3))
        
        # Chuyển đổi sang decimal
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        # Áp dụng dấu dựa trên hướng
        if direction in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    except (ValueError, IndexError):
        return None


def convert_latlon(latlon_str):
    """
    Chuyển đổi tọa độ sang định dạng "lat,lon" (decimal degrees).
    
    This function handles multiple coordinate formats commonly found in Excel files:
    - Decimal degrees (various separators and decimal marks)
    - DMS (Degrees Minutes Seconds) format
    
    Algorithm:
    1. Try to detect DMS format (contains °, ', ")
    2. If DMS, parse and convert each coordinate separately
    3. If decimal, normalize separators and decimal marks
    4. Validate ranges: lat [-90, 90], lon [-180, 180]
    
    Args:
        latlon_str: Coordinate string in various formats
        
    Returns:
        str: Normalized "lat,lon" string or None if invalid
        
    Supported formats:
        1. Decimal: "19.790694,105.778417" or "19.7899904 105.7750516"
        2. European decimal: "19,790694 105,7750516"
        3. Mixed: "19.8014657 105,7761047"
        4. DMS: "19°47'26.5\"N  105°46'42.3\"E"
    """
    if not latlon_str or pd.isna(latlon_str):
        return None
    
    latlon_str = str(latlon_str).strip()
    
    # Kiểm tra xem có phải định dạng DMS không (có chứa ° hoặc ' hoặc " hoặc có N/S/E/W)
    if '°' in latlon_str or "'" in latlon_str or '"' in latlon_str or \
       re.search(r'[NS]', latlon_str, re.IGNORECASE) or re.search(r'[EW]', latlon_str, re.IGNORECASE):
        # Định dạng DMS - cần parse
        # Tìm latitude và longitude trong chuỗi
        # Latitude có N hoặc S, Longitude có E hoặc W
        # Pattern linh hoạt: có thể có hoặc không có dấu °, ', "
        
        # Pattern cho latitude: số độ [°] số phút ['] số giây ["] [N/S]
        lat_pattern = r'(\d+)[°\s]*(\d+)[\'\s]*([\d.]+)[\"\s]*([NS]?)'
        # Pattern cho longitude: số độ [°] số phút ['] số giây ["] [E/W]
        lon_pattern = r'(\d+)[°\s]*(\d+)[\'\s]*([\d.]+)[\"\s]*([EW]?)'
        
        lat_match = re.search(lat_pattern, latlon_str, re.IGNORECASE)
        lon_match = re.search(lon_pattern, latlon_str, re.IGNORECASE)
        
        if lat_match and lon_match:
            # Tạo chuỗi DMS đầy đủ để parse
            lat_dms = f"{lat_match.group(1)}°{lat_match.group(2)}'{lat_match.group(3)}\""
            if lat_match.group(4):
                lat_dms += lat_match.group(4).upper()
            else:
                # Nếu không có hướng, mặc định là N cho latitude
                lat_dms += "N"
            
            lon_dms = f"{lon_match.group(1)}°{lon_match.group(2)}'{lon_match.group(3)}\""
            if lon_match.group(4):
                lon_dms += lon_match.group(4).upper()
            else:
                # Nếu không có hướng, mặc định là E cho longitude
                lon_dms += "E"
            
            lat = dms_to_decimal(lat_dms)
            lon = dms_to_decimal(lon_dms)
            
            if lat is not None and lon is not None:
                return f"{lat:.6f},{lon:.6f}"
        
        return None
    
    else:
        # Định dạng decimal degrees - giữ nguyên hoặc validate
        # Hỗ trợ cả dấu phẩy và dấu cách làm separator
        # Hỗ trợ cả dấu chấm (.) và dấu phẩy (,) làm dấu thập phân
        try:
            # Tách lat và lon
            parts = None
            dot_count = latlon_str.count('.')
            comma_count = latlon_str.count(',')
            has_space = bool(re.search(r'\s+', latlon_str.strip()))
            
            # Ưu tiên 1: Nếu có khoảng trắng -> dùng khoảng trắng làm separator
            if has_space:
                parts = re.split(r'\s+', latlon_str.strip(), maxsplit=1)
            # Ưu tiên 2: Nếu có nhiều dấu chấm (>=2) và 1 dấu phẩy -> dấu chấm là thập phân, dấu phẩy là separator
            elif dot_count >= 2 and comma_count == 1:
                parts = latlon_str.split(',', 1)
            # Ưu tiên 3: Nếu có nhiều dấu phẩy (>=2) và không/ít dấu chấm -> dấu phẩy là thập phân
            # Nhưng không có khoảng trắng -> không thể xác định separator (cần có khoảng trắng hoặc dấu chấm phẩy)
            elif comma_count >= 2 and dot_count < 2:
                # Thử tìm dấu chấm phẩy làm separator
                if ';' in latlon_str:
                    parts = latlon_str.split(';', 1)
                else:
                    # Không có separator rõ ràng -> return None
                    return None
            # Ưu tiên 4: Nếu có 1 dấu phẩy và không có dấu chấm -> dấu phẩy có thể là separator
            elif comma_count == 1 and dot_count == 0:
                parts = latlon_str.split(',', 1)
            # Ưu tiên 5: Chỉ có dấu chấm -> separator là khoảng trắng (nếu có)
            elif dot_count >= 2 and comma_count == 0:
                parts = re.split(r'\s+', latlon_str.strip(), maxsplit=1)
            else:
                # Trường hợp khác: thử split bằng khoảng trắng
                parts = re.split(r'\s+', latlon_str.strip(), maxsplit=1)
            
            if not parts or len(parts) < 2:
                return None
            
            lat_str = parts[0].strip()
            lon_str = parts[1].strip()
            
            # Chuẩn hóa dấu thập phân cho từng phần riêng biệt
            # Mỗi phần (lat/lon) có thể dùng dấu chấm hoặc dấu phẩy làm dấu thập phân
            # Latitude: Xử lý riêng
            if '.' in lat_str:
                # Có dấu chấm -> dấu chấm là thập phân, loại bỏ dấu phẩy
                lat_str = lat_str.replace(',', '')
            elif ',' in lat_str:
                # Chỉ có dấu phẩy -> dấu phẩy là thập phân, chuyển thành dấu chấm
                lat_str = lat_str.replace(',', '.')
            
            # Longitude: Xử lý riêng
            if '.' in lon_str:
                # Có dấu chấm -> dấu chấm là thập phân, loại bỏ dấu phẩy
                lon_str = lon_str.replace(',', '')
            elif ',' in lon_str:
                # Chỉ có dấu phẩy -> dấu phẩy là thập phân, chuyển thành dấu chấm
                lon_str = lon_str.replace(',', '.')
            
            # Loại bỏ khoảng trắng và ký tự không cần thiết, giữ lại dấu trừ và dấu cộng
            lat_str = re.sub(r'[^\d.\-+]', '', lat_str)
            lon_str = re.sub(r'[^\d.\-+]', '', lon_str)
            
            lat = float(lat_str)
            lon = float(lon_str)
            
            # Validate range
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return f"{lat:.6f},{lon:.6f}"
        except (ValueError, IndexError, AttributeError, TypeError):
            pass
    
    return None


def validate_latlon(latlon_str):
    """
    Validate và chuyển đổi format latlon
    Hỗ trợ cả "lat,lon" (decimal) và DMS format
    Trả về True nếu hợp lệ (sau khi chuyển đổi)
    """
    if not latlon_str or pd.isna(latlon_str):
        return True  # Cho phép rỗng
    
    converted = convert_latlon(latlon_str)
    return converted is not None


def validate_phone(phone_str):
    """Validate phone number (cơ bản)"""
    if not phone_str or pd.isna(phone_str):
        return True  # Cho phép rỗng
    # Chấp nhận số điện thoại với các ký tự +, -, khoảng trắng
    phone_clean = re.sub(r'[\s\-\+]', '', str(phone_str))
    return phone_clean.isdigit() and len(phone_clean) >= 8


# =========================
# Routes
# =========================

@import_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("❌ Chưa chọn file", "danger")
            return redirect(url_for("import.index"))

        # Support multiple file types
        filename_lower = file.filename.lower()
        if filename_lower.endswith((".xls", ".xlsx")):
            allowed_ext = {"xls", "xlsx"}
        elif filename_lower.endswith(".csv"):
            allowed_ext = {"csv"}
        elif filename_lower.endswith(".json"):
            allowed_ext = {"json"}
        else:
            allowed_ext = current_app.config.get("ALLOWED_EXTENSIONS", {"xls", "xlsx", "csv", "json"})

        if not allowed_file(file.filename, allowed_ext):
            flash("❌ Chỉ chấp nhận file Excel (.xls, .xlsx), CSV (.csv), hoặc JSON (.json)", "danger")
            return redirect(url_for("import.index"))

        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)

        # Kiểm tra kích thước file
        max_size = current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > max_size:
            flash(f"❌ File quá lớn. Kích thước tối đa: {max_size // 1024 // 1024}MB", "danger")
            return redirect(url_for("import.index"))

        file.save(filepath)

        batch_size = current_app.config.get("IMPORT_BATCH_SIZE", DEFAULT_BATCH_SIZE)
        async_mode = request.form.get("async") == "1"

        if async_mode:
            job_id = start_job(
                process_import,
                current_app._get_current_object(),
                filepath,
                current_user.id,
                batch_size,
                convert_latlon,
                validate_phone,
            )
            return jsonify({"job_id": job_id, "status_url": url_for("import.import_status", job_id=job_id)})

        try:
            result = process_import(
                current_app._get_current_object(),
                filepath,
                current_user.id,
                batch_size,
                convert_latlon,
                validate_phone,
            )
        except (ValueError, KeyError, FileNotFoundError, PermissionError, pd.errors.EmptyDataError) as e:
            flash(f"❌ Lỗi đọc file: {str(e)}", "danger")
            current_app.logger.error(f"File parsing error: {e}", exc_info=True)
            return redirect(url_for("import.index"))
        except Exception as e:
            flash(f"❌ Lỗi không xác định khi đọc file: {str(e)}", "danger")
            current_app.logger.error(f"Unexpected file parsing error: {e}", exc_info=True)
            return redirect(url_for("import.index"))

        flash(f"✅ Import hoàn tất: {result['success']} thành công, {result['errors']} lỗi", "success")
        if result["details"]:
            return render_template("import/result.html", errors=result["details"])

        return redirect(url_for("import.index"))

    return render_template("import/index.html")


@import_bp.route("/status/<job_id>")
@login_required
def import_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@import_bp.route("/clear-errors", methods=["POST"])
def clear_errors():
    """Xóa danh sách lỗi import khỏi session"""
    from flask import session
    session.pop('import_errors', None)
    return redirect(url_for("import.index"))
