"""
Migration script to add latitude/longitude columns for spatial queries.
"""
from app import app
from models import db


with app.app_context():
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns("camera")]

    if "latitude" not in columns:
        db.session.execute(text("ALTER TABLE camera ADD COLUMN latitude FLOAT"))
    if "longitude" not in columns:
        db.session.execute(text("ALTER TABLE camera ADD COLUMN longitude FLOAT"))
    if "require_password_change" not in columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN require_password_change BOOLEAN DEFAULT 0"))

    db.session.commit()
    print("✅ Spatial/user columns updated")
