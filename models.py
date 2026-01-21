from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import json

db = SQLAlchemy()


# =========================
# USER MODEL (GIỮ NGUYÊN)
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="viewer")
    active = db.Column(db.Boolean, default=True)
    # 2FA fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))  # TOTP secret
    # Password policy
    password_changed_at = db.Column(db.DateTime)
    require_password_change = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)  # Account lockout

    def is_admin(self):
        return self.role == "admin"
    
    def is_locked(self):
        """Kiểm tra tài khoản có bị khóa không"""
        if self.locked_until:
            from datetime import datetime
            return datetime.utcnow() < self.locked_until
        return False


# =========================
# CAMERA MODEL (M2 CHUẨN)
# =========================

class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # ===== NHÓM A – ĐỊNH DANH =====
    owner_name = db.Column(db.String(255), index=True)  # Index cho tìm kiếm
    organization_name = db.Column(db.String(255), index=True)  # Index cho tìm kiếm

    address_street = db.Column(db.String(255), index=True)  # Index cho tìm kiếm
    ward = db.Column(db.String(100), index=True)  # Index cho tìm kiếm và group by
    province = db.Column(db.String(100), index=True)  # Index cho tìm kiếm
    phone = db.Column(db.String(50))

    camera_index = db.Column(db.Integer)
    system_type = db.Column(db.String(255), index=True)  # Index cho tìm kiếm và group by

    # ===== NHÓM B – CHẾ ĐỘ & LƯU TRỮ (JSON TEXT) =====
    monitoring_modes = db.Column(db.Text)     # ["Xem qua Internet", "Ghi"]
    storage_types = db.Column(db.Text)        # ["Đầu ghi", "Đám mây"]
    retention_days = db.Column(db.Integer)    # 30

    # ===== NHÓM C – THÔNG SỐ KỸ THUẬT =====
    manufacturer = db.Column(db.String(100))

    camera_types = db.Column(db.Text)          # ["IP"]
    form_factors = db.Column(db.Text)          # ["Hộp ngoài", "Thân trụ"]
    network_types = db.Column(db.Text)         # ["Có dây", "Wifi"]

    # ===== NHÓM D – VỊ TRÍ =====
    install_areas = db.Column(db.Text)         # ["Cổng và vỉa hè"]
    latlon = db.Column(db.String(50), index=True)  # "19.8,105.77" - Index cho tìm kiếm camera có tọa độ
    latitude = db.Column(db.Float, index=True)
    longitude = db.Column(db.Float, index=True)

    # ===== NHÓM E – TÀI KHOẢN / KẾT NỐI =====
    login_user = db.Column(db.String(100))
    login_password = db.Column(db.String(100))
    login_domain = db.Column(db.String(255))
    static_ip = db.Column(db.String(50))
    ip_port = db.Column(db.String(50))
    dvr_model = db.Column(db.String(100))
    camera_model = db.Column(db.String(100))

    # ===== NHÓM F – ĐÁNH GIÁ =====
    resolution = db.Column(db.String(50))
    bandwidth = db.Column(db.String(50))
    serial_number = db.Column(db.String(100))
    verification_code = db.Column(db.String(100))   # Mã xác minh
    category = db.Column(db.String(50))
    sharing_scope = db.Column(db.Boolean, default=False)

    # =========================
    # HELPER METHODS
    # =========================

    def set_json(self, field_name, value):
        """Lưu list → JSON string"""
        setattr(self, field_name, json.dumps(value, ensure_ascii=False))

    def get_json(self, field_name):
        """Đọc JSON string → list"""
        val = getattr(self, field_name)
        if not val:
            return []
        try:
            return json.loads(val)
        except:
            return []

    def set_latlon_components(self):
        """Parse latlon string and store latitude/longitude if available."""
        if not self.latlon:
            return
        try:
            lat_str, lon_str = self.latlon.split(",", 1)
            self.latitude = float(lat_str.strip())
            self.longitude = float(lon_str.strip())
        except Exception:
            self.latitude = None
            self.longitude = None


# =========================
# SECURITY MODELS
# =========================

class LoginHistory(db.Model):
    """Lịch sử đăng nhập"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.String(255))
    login_time = db.Column(db.DateTime, nullable=False, default=db.func.now())
    success = db.Column(db.Boolean, default=True)
    failure_reason = db.Column(db.String(255))  # Lý do thất bại nếu có
    
    user = db.relationship('User', backref='login_history')


class AuditLog(db.Model):
    """Audit log cho các thao tác quan trọng"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(100))
    action = db.Column(db.String(50), nullable=False)  # 'import', 'export', 'delete', 'create', 'edit'
    resource_type = db.Column(db.String(50))  # 'camera', 'user', etc.
    resource_id = db.Column(db.Integer)  # ID của resource bị tác động
    ip_address = db.Column(db.String(45))
    details = db.Column(db.Text)  # JSON string với thông tin chi tiết
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())
    
    user = db.relationship('User', backref='audit_logs')
