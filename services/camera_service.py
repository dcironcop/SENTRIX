from sqlalchemy import func

from models import Camera, db
from security_utils import log_audit
from import_data import convert_latlon


class CameraService:
    @staticmethod
    def search_cameras(filters, page=1, per_page=50):
        query = Camera.query

        text_fields = [
            "owner_name",
            "organization_name",
            "address_street",
            "ward",
            "province",
            "phone",
            "manufacturer",
            "latlon",
            "static_ip",
        ]
        for field in text_fields:
            value = filters.get(field)
            if value:
                query = query.filter(getattr(Camera, field).ilike(f"%{value}%"))

        json_fields = [
            "monitoring_modes",
            "storage_types",
            "camera_types",
            "form_factors",
            "network_types",
            "install_areas",
        ]
        for field in json_fields:
            values = filters.get(field, [])
            if values:
                for val in values:
                    query = query.filter(getattr(Camera, field).ilike(f"%{val}%"))

        pagination = query.order_by(Camera.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return pagination.items, pagination.total, pagination

    @staticmethod
    def get_camera_by_id(camera_id):
        return Camera.query.get(camera_id)

    @staticmethod
    def get_cameras_by_ids(ids):
        if not ids:
            return []
        return Camera.query.filter(Camera.id.in_(ids)).all()

    @staticmethod
    def create_camera(camera_data, json_fields, user_id=None):
        latlon_value = camera_data.get("latlon")
        if latlon_value:
            converted = convert_latlon(latlon_value)
            camera_data["latlon"] = converted or latlon_value

        cam = Camera(**camera_data)
        for field_name, value in json_fields.items():
            cam.set_json(field_name, value)
        cam.set_latlon_components()
        db.session.add(cam)
        db.session.commit()
        if user_id:
            log_audit("create", "camera", cam.id, {"action": "create"}, user=None)
        return cam

    @staticmethod
    def update_camera(camera_id, camera_data, json_fields, user_id=None):
        camera = Camera.query.get(camera_id)
        if not camera:
            return None

        latlon_value = camera_data.get("latlon")
        if latlon_value:
            converted = convert_latlon(latlon_value)
            camera_data["latlon"] = converted or latlon_value

        for key, value in camera_data.items():
            setattr(camera, key, value)

        for field_name, value in json_fields.items():
            camera.set_json(field_name, value)
        camera.set_latlon_components()
        db.session.commit()
        if user_id:
            log_audit("edit", "camera", camera.id, {"action": "update"}, user=None)
        return camera

    @staticmethod
    def delete_camera(camera_id, user_id=None):
        camera = Camera.query.get(camera_id)
        if not camera:
            return False
        db.session.delete(camera)
        db.session.commit()
        if user_id:
            log_audit("delete", "camera", camera_id, {"action": "delete"}, user=None)
        return True

    @staticmethod
    def get_wards_with_counts():
        return (
            db.session.query(Camera.ward, func.count(Camera.id))
            .group_by(Camera.ward)
            .order_by(Camera.ward)
            .all()
        )

    @staticmethod
    def get_cameras_by_ward(ward):
        return Camera.query.filter_by(ward=ward).all()
