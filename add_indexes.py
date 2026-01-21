"""
Script để thêm database indexes cho các trường tìm kiếm thường dùng.
Chạy script này sau khi cập nhật models.py để tạo indexes.

Usage:
    python add_indexes.py
"""

from app import app
from models import db, Camera
from sqlalchemy import Index

def add_indexes():
    """Thêm indexes cho các trường tìm kiếm thường dùng"""
    with app.app_context():
        try:
            # Tạo indexes nếu chưa tồn tại
            # SQLite sẽ tự động tạo indexes từ index=True trong model definition
            # Nhưng để đảm bảo, ta có thể tạo thủ công cho các database khác
            
            # Kiểm tra xem indexes đã tồn tại chưa
            inspector = db.inspect(db.engine)
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('camera')]
            
            indexes_to_create = []
            
            # Index cho owner_name
            if 'ix_camera_owner_name' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_owner_name', Camera.owner_name)
                )
            
            # Index cho organization_name
            if 'ix_camera_organization_name' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_organization_name', Camera.organization_name)
                )
            
            # Index cho address_street
            if 'ix_camera_address_street' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_address_street', Camera.address_street)
                )
            
            # Index cho ward
            if 'ix_camera_ward' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_ward', Camera.ward)
                )
            
            # Index cho province
            if 'ix_camera_province' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_province', Camera.province)
                )
            
            # Index cho system_type
            if 'ix_camera_system_type' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_system_type', Camera.system_type)
                )
            
            # Index cho latlon
            if 'ix_camera_latlon' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_latlon', Camera.latlon)
                )

            if 'ix_camera_latitude' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_latitude', Camera.latitude)
                )

            if 'ix_camera_longitude' not in existing_indexes:
                indexes_to_create.append(
                    Index('ix_camera_longitude', Camera.longitude)
                )
            
            # Tạo các indexes
            if indexes_to_create:
                print(f"Creating {len(indexes_to_create)} indexes...")
                for idx in indexes_to_create:
                    try:
                        idx.create(db.engine)
                        print(f"✓ Created index: {idx.name}")
                    except Exception as e:
                        print(f"✗ Failed to create index {idx.name}: {e}")
                print("Done!")
            else:
                print("All indexes already exist. No action needed.")
                
        except Exception as e:
            print(f"Error creating indexes: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    add_indexes()
