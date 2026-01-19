import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, url_for, render_template, request
from flask_login import LoginManager, current_user
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User
from export import export_bp
from config import config

# ===== IMPORT BLUEPRINTS =====
from auth import auth_bp
from camera import camera_bp
from map_view import map_bp
from dashboard import dashboard_bp
from import_data import import_bp
from user_admin import user_bp
from about import about_bp
from data_quality_bp import data_quality_bp

# ===== CREATE APP =====
app = Flask(__name__)

# Load config từ environment variable hoặc dùng 'development'
env = os.environ.get('FLASK_ENV', 'development')
config_class = config.get(env, config['default'])
app.config.from_object(config_class)

# Kiểm tra SECRET_KEY cho production
if env == 'production' and not app.config.get('SECRET_KEY'):
    raise ValueError("SECRET_KEY must be set in production environment! Set FLASK_ENV=production and SECRET_KEY=...")

# ===== INIT DATABASE =====
db.init_app(app)

# ===== INIT CACHE =====
cache = Cache()
# Cấu hình cache: ưu tiên Redis nếu có, nếu không dùng SimpleCache (in-memory)
cache_type = os.environ.get('CACHE_TYPE', app.config.get('CACHE_TYPE', 'SimpleCache'))
if cache_type == 'RedisCache':
    try:
        cache.init_app(app, config={
            'CACHE_TYPE': 'RedisCache',
            'CACHE_REDIS_URL': app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379/0'),
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        })
        app.logger.info('Redis cache initialized')
    except Exception as e:
        app.logger.warning(f'Failed to initialize Redis cache, falling back to SimpleCache: {e}')
        cache.init_app(app, config={
            'CACHE_TYPE': 'SimpleCache',
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        })
else:
    cache.init_app(app, config={
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
    })

# Đảm bảo cache được thêm vào extensions
if 'cache' not in app.extensions:
    app.extensions['cache'] = cache

# ===== CSRF PROTECTION =====
# Chỉ bật CSRF cho production hoặc khi được cấu hình
csrf_enabled = app.config.get('WTF_CSRF_ENABLED', True)
if csrf_enabled:
    csrf = CSRFProtect(app)
    # Expose csrf_token function to templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
else:
    csrf = None

# ===== RATE LIMITING =====
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=app.config.get('RATELIMIT_STORAGE_URL') or "memory://"
)

# ===== LOGIN MANAGER =====
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ===== HOME ROUTE (FIX 404) =====
@app.route("/")
def home():
    """
    Trang gốc:
    - Chưa đăng nhập → chuyển login
    - Đã đăng nhập → chuyển Tra cứu camera
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))

# (không bắt buộc – chỉ để khỏi log 404 favicon)
@app.route("/favicon.ico")
def favicon():
    return "", 204

# ===== API DOCUMENTATION =====
# Initialize API documentation (Swagger/OpenAPI)
try:
    from flask_restx import Api
    api = Api(
        app,
        version='1.0',
        title='Sentrix API',
        description='API documentation for Sentrix Camera Management System',
        doc='/api/docs/',
        prefix='/api'
    )
    
    # Register API namespaces
    try:
        from api import camera_api, auth_api
        api.add_namespace(camera_api.ns)
        api.add_namespace(auth_api.ns)
    except ImportError:
        # API modules not available
        pass
except ImportError:
    # Flask-RESTX not installed, skip API docs
    api = None

# ===== REGISTER BLUEPRINTS =====
app.register_blueprint(auth_bp)
app.register_blueprint(camera_bp)
app.register_blueprint(map_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(import_bp)
app.register_blueprint(user_bp)
app.register_blueprint(export_bp)
app.register_blueprint(about_bp)
app.register_blueprint(data_quality_bp)

# ===== ERROR HANDLERS =====
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403


# ===== LOGGING =====
if not app.debug:
    # Tạo thư mục logs nếu chưa có
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Cấu hình file handler với rotation
    file_handler = RotatingFileHandler('logs/sentrix.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('SENTRIX startup')

# ===== RUN APP =====
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=app.config.get('DEBUG', False))
