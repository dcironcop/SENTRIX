"""
Migration script để thêm các bảng và cột bảo mật mới
Chạy script này để cập nhật database với các tính năng bảo mật
"""
from app import app
from models import db, User, LoginHistory, AuditLog

with app.app_context():
    print("🔄 Đang tạo các bảng bảo mật mới...")
    
    # Tạo các bảng mới
    try:
        db.create_all()
        print("✅ Đã tạo các bảng: LoginHistory, AuditLog")
    except Exception as e:
        print(f"⚠️ Lỗi khi tạo bảng: {e}")
    
    # Thêm các cột mới vào bảng User nếu chưa có
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'two_factor_enabled' not in columns:
            print("🔄 Đang thêm cột two_factor_enabled...")
            db.session.execute(text("ALTER TABLE user ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0"))
            db.session.commit()
            print("✅ Đã thêm cột two_factor_enabled")
        
        if 'two_factor_secret' not in columns:
            print("🔄 Đang thêm cột two_factor_secret...")
            db.session.execute(text("ALTER TABLE user ADD COLUMN two_factor_secret VARCHAR(32)"))
            db.session.commit()
            print("✅ Đã thêm cột two_factor_secret")
        
        if 'password_changed_at' not in columns:
            print("🔄 Đang thêm cột password_changed_at...")
            db.session.execute(text("ALTER TABLE user ADD COLUMN password_changed_at DATETIME"))
            db.session.commit()
            print("✅ Đã thêm cột password_changed_at")
        
        if 'failed_login_attempts' not in columns:
            print("🔄 Đang thêm cột failed_login_attempts...")
            db.session.execute(text("ALTER TABLE user ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"))
            db.session.commit()
            print("✅ Đã thêm cột failed_login_attempts")
        
        if 'locked_until' not in columns:
            print("🔄 Đang thêm cột locked_until...")
            db.session.execute(text("ALTER TABLE user ADD COLUMN locked_until DATETIME"))
            db.session.commit()
            print("✅ Đã thêm cột locked_until")
        
        print("✅ Hoàn tất migration!")
        
    except Exception as e:
        print(f"⚠️ Lỗi khi thêm cột: {e}")
        db.session.rollback()
