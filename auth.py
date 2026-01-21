from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64

from models import db, User
from security_utils import log_audit
from security_utils import log_login, validate_password, sanitize_input, get_client_ip

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = sanitize_input(request.form.get("username", ""))
        password = request.form.get("password", "")
        two_factor_code = request.form.get("two_factor_code", "")

        user = User.query.filter_by(username=username).first()
        
        # Kiểm tra tài khoản bị khóa
        if user and user.is_locked():
            flash("❌ Tài khoản đã bị khóa do đăng nhập sai nhiều lần. Vui lòng thử lại sau.", "danger")
            log_login(user, success=False, failure_reason="Account locked")
            return render_template("auth/login.html")
        
        # Kiểm tra username và password
        if user and user.active and check_password_hash(user.password, password):
            # Reset failed login attempts
            user.failed_login_attempts = 0
            user.locked_until = None
            
            # Kiểm tra 2FA nếu đã bật
            if user.two_factor_enabled:
                if not two_factor_code:
                    # Cần nhập 2FA code
                    session['pending_user_id'] = user.id
                    return render_template("auth/login.html", require_2fa=True, username=username)
                
                # Verify 2FA code
                totp = pyotp.TOTP(user.two_factor_secret)
                if not totp.verify(two_factor_code, valid_window=1):
                    flash("❌ Mã xác thực 2FA không đúng", "danger")
                    log_login(user, success=False, failure_reason="Invalid 2FA code")
                    return render_template("auth/login.html", require_2fa=True, username=username)
            
            # Đăng nhập thành công
            login_user(user, remember=True)
            session.permanent = True
            log_login(user, success=True)
            flash("✅ Đăng nhập thành công", "success")
            if user.require_password_change:
                return redirect(url_for("auth.change_password"))
            return redirect(url_for("dashboard.index"))
        else:
            # Đăng nhập thất bại
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
                if user.failed_login_attempts >= max_attempts:
                    lockout_duration = current_app.config.get('LOCKOUT_DURATION', timedelta(minutes=30))
                    user.locked_until = datetime.utcnow() + lockout_duration
                    flash(f"❌ Tài khoản đã bị khóa do đăng nhập sai {max_attempts} lần. Vui lòng thử lại sau {lockout_duration.seconds // 60} phút.", "danger")
                else:
                    remaining = max_attempts - user.failed_login_attempts
                    flash(f"❌ Sai tài khoản hoặc mật khẩu. Còn {remaining} lần thử.", "danger")
                db.session.commit()
            else:
                flash("❌ Sai tài khoản hoặc mật khẩu", "danger")
            
            log_login(user if user else None, success=False, failure_reason="Invalid credentials")

    return render_template("auth/login.html")


@auth_bp.before_app_request
def enforce_password_change():
    if not current_user.is_authenticated:
        return None
    if not current_user.require_password_change:
        return None

    allowed_endpoints = {
        "auth.change_password",
        "auth.logout",
        "auth.login",
        "static",
    }
    if request.endpoint in allowed_endpoints or request.endpoint is None:
        return None
    return redirect(url_for("auth.change_password"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password or new_password != confirm_password:
            flash("❌ Mật khẩu xác nhận không khớp", "danger")
            return render_template("auth/change_password.html")

        is_valid, error_msg = validate_password(
            new_password,
            min_length=current_app.config.get("PASSWORD_MIN_LENGTH", 8),
            require_uppercase=current_app.config.get("PASSWORD_REQUIRE_UPPERCASE", True),
            require_lowercase=current_app.config.get("PASSWORD_REQUIRE_LOWERCASE", True),
            require_number=current_app.config.get("PASSWORD_REQUIRE_NUMBER", True),
            require_special=current_app.config.get("PASSWORD_REQUIRE_SPECIAL", True),
        )
        if not is_valid:
            flash(f"❌ {error_msg}", "danger")
            return render_template("auth/change_password.html")

        current_user.password = generate_password_hash(new_password)
        current_user.require_password_change = False
        current_user.password_changed_at = datetime.utcnow()
        db.session.commit()
        log_audit("edit", "user", current_user.id, {"action": "change_password"})
        flash("✅ Đổi mật khẩu thành công", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Đã đăng xuất", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/setup-2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    """Setup 2FA cho user"""
    user = current_user
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "enable":
            # Generate secret nếu chưa có
            if not user.two_factor_secret:
                user.two_factor_secret = pyotp.random_base32()
                db.session.commit()
            
            # Generate QR code
            totp = pyotp.TOTP(user.two_factor_secret)
            provisioning_uri = totp.provisioning_uri(
                name=user.username,
                issuer_name="Sentrix"
            )
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            
            return render_template("auth/setup_2fa.html", qr_code=qr_code_data, secret=user.two_factor_secret)
        
        elif action == "verify":
            code = request.form.get("code", "")
            if not user.two_factor_secret:
                flash("❌ Chưa tạo secret. Vui lòng bấm 'Bật 2FA' trước.", "danger")
                return redirect(url_for("auth.setup_2fa"))
            
            totp = pyotp.TOTP(user.two_factor_secret)
            if totp.verify(code, valid_window=1):
                user.two_factor_enabled = True
                db.session.commit()
                flash("✅ Đã bật xác thực 2 yếu tố thành công", "success")
                return redirect(url_for("dashboard.index"))
            else:
                flash("❌ Mã xác thực không đúng. Vui lòng thử lại.", "danger")
        
        elif action == "disable":
            code = request.form.get("code", "")
            if not user.two_factor_secret:
                flash("❌ 2FA chưa được bật", "danger")
                return redirect(url_for("auth.setup_2fa"))
            
            totp = pyotp.TOTP(user.two_factor_secret)
            if totp.verify(code, valid_window=1):
                user.two_factor_enabled = False
                user.two_factor_secret = None
                db.session.commit()
                flash("✅ Đã tắt xác thực 2 yếu tố", "success")
                return redirect(url_for("dashboard.index"))
            else:
                flash("❌ Mã xác thực không đúng. Vui lòng thử lại.", "danger")
    
    return render_template("auth/setup_2fa.html", 
                         two_factor_enabled=user.two_factor_enabled,
                         has_secret=bool(user.two_factor_secret))


@auth_bp.route("/login-history")
@login_required
def login_history():
    """Xem lịch sử đăng nhập của user hiện tại"""
    from models import LoginHistory
    
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('CAMERAS_PER_PAGE', 50)
    
    pagination = LoginHistory.query.filter_by(user_id=current_user.id)\
        .order_by(LoginHistory.login_time.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template("auth/login_history.html", pagination=pagination)
