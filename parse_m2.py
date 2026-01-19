import pandas as pd
import re


# =========================
# Helper functions
# =========================

def is_checked(value):
    """Check if a cell is ticked (x, X, ✓)"""
    if pd.isna(value):
        return False
    return str(value).strip().lower() in ["x", "✓"]


def is_number(value):
    """
    Kiểm tra một giá trị có thể chuyển sang số nguyên hay không.
    Hỗ trợ cả trường hợp ô chứa chuỗi dạng 'Camera 01' hoặc '(16)' -> vẫn coi là số.
    """
    if pd.isna(value):
        return False
    s = str(value).strip()
    # Nếu toàn bộ là số
    if s.isdigit():
        return True
    # Nếu chuỗi có số bên trong (ví dụ 'Camera 01', '(16)') thì vẫn coi là số
    m = re.search(r"\d+", s)
    return m is not None


def extract_number(value):
    """
    Trích xuất số từ một giá trị có thể chứa ký tự không phải số.
    Ví dụ: 'Camera 01' -> 1, '(16)' -> 16, '30' -> 30
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    # Tìm số đầu tiên trong chuỗi
    m = re.search(r"\d+", s)
    if m:
        return int(m.group())
    return None


# =========================
# Main parser
# =========================

def parse_m2_to_records(excel_path):
    """
    Đọc file M2 và trả về list dict camera đã chuẩn hóa
    """
    df = pd.read_excel(excel_path, header=None)
    records = []

    current_system = None

    for idx, row in df.iterrows():
        first_cell = str(row[0]).strip()

        # -----------------------------
        # 1. Dòng hệ thống camera
        # -----------------------------
        if re.match(r"^(I|II|III|IV|V|VI)\.", first_cell):
            current_system = first_cell
            continue

        # -----------------------------
        # 2. Bỏ qua dòng không phải camera
        # -----------------------------
        if not is_number(row[0]):
            continue

        # -----------------------------
        # 3. Parse nhóm A
        # -----------------------------
        owner_name = row[1]
        organization_name = row[2]
        address_street = row[3]
        ward = row[4]
        province = row[5]
        phone = row[6]

        # Thứ tự camera (có thể ô là 'Camera 01' hoặc '(1)' → lấy phần số)
        camera_index = extract_number(row[7])
        if camera_index is None:
            raise ValueError(f"Thiếu hoặc thứ tự camera không hợp lệ: {row[7]}")
        system_type = current_system

        # -----------------------------
        # 4. Nhóm B – Chế độ giám sát
        # -----------------------------
        monitoring_modes = []
        if is_checked(row[9]):
            monitoring_modes.append("Xem qua Internet")
        if is_checked(row[10]):
            monitoring_modes.append("Xem cục bộ")
        if is_checked(row[11]):
            monitoring_modes.append("Ghi")

        # -----------------------------
        # 5. Nhóm B – Lưu trữ
        # -----------------------------
        storage_types = []
        if is_checked(row[12]):
            storage_types.append("Đầu ghi")
        if is_checked(row[13]):
            storage_types.append("Thẻ nhớ")
        if is_checked(row[14]):
            storage_types.append("Đám mây")

        retention_days = None
        if is_number(row[15]):
            retention_days = extract_number(row[15])

        # -----------------------------
        # 6. Nhóm C – Thông số kỹ thuật
        # -----------------------------
        manufacturer = row[16]

        camera_types = []
        if is_checked(row[17]):
            camera_types.append("Analog")
        if is_checked(row[18]):
            camera_types.append("IP")

        form_factors = []
        if is_checked(row[19]):
            form_factors.append("Hộp ngoài")
        if is_checked(row[20]):
            form_factors.append("Thân trụ")
        if is_checked(row[21]):
            form_factors.append("Bán cầu")

        network_types = []
        if is_checked(row[22]):
            network_types.append("Có dây")
        if is_checked(row[23]):
            network_types.append("Wifi")
        if is_checked(row[24]):
            network_types.append("Di động")

        # -----------------------------
        # 7. Nhóm D – Vị trí lắp đặt
        # -----------------------------
        install_areas = []
        if is_checked(row[26]):
            install_areas.append("Cổng và vỉa hè")
        if is_checked(row[27]):
            install_areas.append("Ngoài đường")

        latlon = row[28]

        # -----------------------------
        # 8. Nhóm E – Tài khoản / kết nối
        # -----------------------------
        login_user = row[29]
        login_password = row[30]
        login_domain = row[31]
        static_ip = row[32]
        ip_port = row[33]
        dvr_model = row[34]
        camera_model = row[35]

        # -----------------------------
        # 9. Nhóm F – Đánh giá / phân loại
        # -----------------------------
        resolution = row[36]
        bandwidth = row[37]
        serial_number = row[38]
        verification_code = row[39]
        category = row[40]
        sharing_scope = is_checked(row[41])

        # -----------------------------
        # 10. Build record
        # -----------------------------
        record = {
            "owner_name": owner_name,
            "organization_name": organization_name,
            "address_street": address_street,
            "ward": ward,
            "province": province,
            "phone": phone,

            "camera_index": camera_index,
            "system_type": system_type,

            "monitoring_modes": monitoring_modes,
            "storage_types": storage_types,
            "retention_days": retention_days,

            "manufacturer": manufacturer,
            "camera_types": camera_types,
            "form_factors": form_factors,
            "network_types": network_types,

            "install_areas": install_areas,
            "latlon": latlon,

            "login_user": login_user,
            "login_password": login_password,
            "login_domain": login_domain,
            "static_ip": static_ip,
            "ip_port": ip_port,
            "dvr_model": dvr_model,
            "camera_model": camera_model,

            "resolution": resolution,
            "bandwidth": bandwidth,
            "serial_number": serial_number,
            "verification_code": verification_code,
            "category": category,
            "sharing_scope": sharing_scope,
        }

        records.append(record)

    return records
