import os
from datetime import timedelta


class Config:
    """Cấu hình cơ bản cho ứng dụng"""
    # Secret key - ưu tiên từ environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///sentrix.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 2 giờ timeout
    SESSION_TIMEOUT_WARNING = timedelta(minutes=10)  # Cảnh báo 10 phút trước khi hết hạn
    
    # Security
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBER = True
    PASSWORD_REQUIRE_SPECIAL = True
    MAX_LOGIN_ATTEMPTS = 5  # Số lần đăng nhập sai tối đa
    LOCKOUT_DURATION = timedelta(minutes=30)  # Khóa tài khoản 30 phút
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = None  # Sẽ dùng memory nếu không có Redis
    
    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 giờ
    
    # Pagination
    CAMERAS_PER_PAGE = 50
    
    # Import batch size for transaction management
    # Commit database every N records instead of all at once
    # Improves performance and reduces memory usage for large imports
    IMPORT_BATCH_SIZE = 100
    
    # Map
    DEFAULT_MAP_CENTER_LAT = 20.0
    DEFAULT_MAP_CENTER_LON = 105.0
    DEFAULT_MAP_ZOOM = 6
    
    # Caching
    CACHE_TYPE = "SimpleCache"  # Default: SimpleCache (in-memory), hoặc "RedisCache" nếu có Redis
    CACHE_DEFAULT_TIMEOUT = 300  # 5 phút
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'


class DevelopmentConfig(Config):
    """Cấu hình cho môi trường development"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Cấu hình cho môi trường production"""
    DEBUG = False
    TESTING = False
    # Trong production, SECRET_KEY sẽ được check ở app.py khi load config


class TestingConfig(Config):
    """Cấu hình cho môi trường testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'


# Dictionary để chọn config theo môi trường
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

