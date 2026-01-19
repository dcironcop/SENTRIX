from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User

user_bp = Blueprint("user", __name__, url_prefix="/users")

def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash("Chỉ admin mới được truy cập chức năng này", "danger")
        return False
    return True


@user_bp.route("/")
@login_required
def manage_users():
    if not admin_required():
        return redirect(url_for("dashboard.index"))

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('CAMERAS_PER_PAGE', 50)  # Dùng cùng config
    
    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    # Helper function để build pagination URL
    def build_pagination_url(page_num):
        """Build URL với tất cả query params hiện tại, chỉ thay đổi page"""
        args = request.args.copy()
        args['page'] = page_num
        return url_for('user.manage_users', **args)
    
    return render_template("user/manage.html", users=users, pagination=pagination, build_pagination_url=build_pagination_url)


@user_bp.route("/create", methods=["POST"])
@login_required
def create_user():
    if not admin_required():
        return redirect(url_for("dashboard.index"))

    username = sanitize_input(request.form.get("username", ""))
    password = request.form.get("password", "")
    role = sanitize_input(request.form.get("role", "viewer"))

    if not username:
        flash("Tên đăng nhập không được để trống", "danger")
        return redirect(url_for("user.manage_users"))

    if User.query.filter_by(username=username).first():
        flash("Tên đăng nhập đã tồn tại", "warning")
        return redirect(url_for("user.manage_users"))

    # Validate password
    config = current_app.config
    is_valid, error_msg = validate_password(
        password,
        min_length=config.get('PASSWORD_MIN_LENGTH', 8),
        require_uppercase=config.get('PASSWORD_REQUIRE_UPPERCASE', True),
        require_lowercase=config.get('PASSWORD_REQUIRE_LOWERCASE', True),
        require_number=config.get('PASSWORD_REQUIRE_NUMBER', True),
        require_special=config.get('PASSWORD_REQUIRE_SPECIAL', True)
    )
    
    if not is_valid:
        flash(f"❌ {error_msg}", "danger")
        return redirect(url_for("user.manage_users"))

    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role,
        password_changed_at=datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()
    
    # Log audit
    log_audit('create', 'user', user.id, {'username': username, 'role': role})
    
    flash("Tạo tài khoản thành công", "success")
    return redirect(url_for("user.manage_users"))


@user_bp.route("/toggle/<int:user_id>")
@login_required
def toggle_user(user_id):
    if not admin_required():
        return redirect(url_for("dashboard.index"))

    user = User.query.get_or_404(user_id)
    user.active = not user.active
    db.session.commit()
    return redirect(url_for("user.manage_users"))
