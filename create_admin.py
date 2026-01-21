from app import app
from models import db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # kiểm tra đã có admin chưa
    admin = User.query.filter_by(username="admin").first()
    if admin:
        print("⚠️ Tài khoản admin đã tồn tại")
    else:
        admin = User(
            username="admin",
            password=generate_password_hash("123456"),
            role="admin",
            active=True,
            require_password_change=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Đã tạo tài khoản admin / 123456")
