"""
Security utilities for Sentrix

This module provides security-related utility functions:
- Password validation: Enforces password policy
- Input sanitization: Prevents XSS and injection attacks
- Audit logging: Tracks important operations
- Login history: Records login attempts

Security Features:
    - Password complexity requirements
    - HTML/script tag removal
    - IP address tracking
    - User action auditing

Example usage:
    from security_utils import validate_password, sanitize_input, log_audit
    
    # Validate password
    is_valid, error = validate_password('MyPass123!')
    
    # Sanitize input
    clean = sanitize_input('<script>alert("xss")</script>Hello')
    
    # Log audit
    log_audit('create', 'camera', 1, {'action': 'created'})
"""
import re
import bleach
from datetime import datetime
from flask import request, current_app
from models import db, AuditLog, LoginHistory, User


def validate_password(password, min_length=8, require_uppercase=True, 
                      require_lowercase=True, require_number=True, 
                      require_special=True):
    """
    Validate password theo policy
    
    Returns:
        (is_valid, error_message)
    """
    errors = []
    
    if len(password) < min_length:
        errors.append(f"Mật khẩu phải có ít nhất {min_length} ký tự")
    
    if require_uppercase and not re.search(r'[A-Z]', password):
        errors.append("Mật khẩu phải có ít nhất 1 chữ hoa")
    
    if require_lowercase and not re.search(r'[a-z]', password):
        errors.append("Mật khẩu phải có ít nhất 1 chữ thường")
    
    if require_number and not re.search(r'\d', password):
        errors.append("Mật khẩu phải có ít nhất 1 số")
    
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Mật khẩu phải có ít nhất 1 ký tự đặc biệt (!@#$%^&*...)")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, None


def sanitize_input(text, max_length=None):
    """
    Sanitize user input để tránh XSS và injection
    """
    if not text:
        return ""
    
    # Loại bỏ HTML tags và chỉ giữ text
    cleaned = bleach.clean(text, tags=[], strip=True)
    
    # Giới hạn độ dài nếu có
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned


def sanitize_search_input(text):
    """
    Sanitize input cho search queries (cho phép một số ký tự đặc biệt)
    """
    if not text:
        return ""
    
    # Loại bỏ các ký tự nguy hiểm nhưng giữ lại ký tự hợp lệ cho search
    # Cho phép: chữ, số, khoảng trắng, dấu câu cơ bản
    cleaned = re.sub(r'[<>"\']', '', text)
    cleaned = bleach.clean(cleaned, tags=[], strip=True)
    
    return cleaned[:255]  # Giới hạn độ dài


def log_login(user, success=True, failure_reason=None):
    """
    Log lịch sử đăng nhập
    """
    try:
        login_history = LoginHistory(
            user_id=user.id if user and success else None,
            username=user.username if user else request.form.get('username', 'unknown'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:255],
            login_time=datetime.utcnow(),
            success=success,
            failure_reason=failure_reason
        )
        db.session.add(login_history)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log login: {e}")
        db.session.rollback()


def log_audit(action, resource_type=None, resource_id=None, details=None, user=None):
    """
    Log audit cho các thao tác quan trọng
    
    Args:
        action: 'import', 'export', 'delete', 'create', 'edit'
        resource_type: 'camera', 'user', etc.
        resource_id: ID của resource bị tác động
        details: Dict hoặc string với thông tin chi tiết
        user: User object (mặc định dùng current_user)
    """
    try:
        from flask_login import current_user
        
        # Kiểm tra current_user có authenticated không
        if user:
            audit_user = user
        else:
            try:
                audit_user = current_user if current_user.is_authenticated else None
            except (AttributeError, RuntimeError):
                # current_user not available in this context
                audit_user = None
        
        # Convert details to JSON string nếu là dict
        if isinstance(details, dict):
            import json
            details = json.dumps(details, ensure_ascii=False)
        
        audit_log = AuditLog(
            user_id=audit_user.id if audit_user and hasattr(audit_user, 'id') else None,
            username=audit_user.username if audit_user and hasattr(audit_user, 'username') else 'anonymous',
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=get_client_ip(),
            details=details,
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_log)
        db.session.commit()
    except (SQLAlchemyError, IntegrityError) as e:
        current_app.logger.error(f"Database error logging audit: {e}")
        db.session.rollback()
    except Exception as e:
        # Catch-all for unexpected errors
        current_app.logger.error(f"Unexpected error logging audit: {e}", exc_info=True)
        db.session.rollback()


def get_client_ip():
    """
    Lấy IP address của client (hỗ trợ proxy)
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr
