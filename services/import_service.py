import os

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import Camera, db
from parse_m2 import parse_m2_to_records
from security_utils import log_audit


def process_import(
    app,
    filepath,
    user_id=None,
    batch_size=100,
    convert_latlon_func=None,
    validate_phone_func=None,
):
    success = 0
    errors = 0
    error_details = []
    batch_count = 0

    with app.app_context():
        records = parse_m2_to_records(filepath)
        total_records = len(records)
        app.logger.info(
            "Starting import of %s records with batch size %s",
            total_records,
            batch_size,
        )

        for idx, record in enumerate(records, start=1):
            try:
                if not record.get("system_type"):
                    raise ValueError("Thiếu hệ thống camera")

                if record.get("camera_index") is None:
                    raise ValueError("Thiếu thứ tự camera")

                latlon_value = record.get("latlon")
                if latlon_value and convert_latlon_func:
                    converted_latlon = convert_latlon_func(latlon_value)
                    if converted_latlon:
                        latlon_value = converted_latlon
                    else:
                        raise ValueError(f"Tọa độ không hợp lệ: {record.get('latlon')}")

                if record.get("phone") and validate_phone_func:
                    if not validate_phone_func(record.get("phone")):
                        raise ValueError(f"Số điện thoại không hợp lệ: {record.get('phone')}")

                cam = Camera(
                    owner_name=record.get("owner_name"),
                    organization_name=record.get("organization_name"),
                    address_street=record.get("address_street"),
                    ward=record.get("ward"),
                    province=record.get("province"),
                    phone=record.get("phone"),
                    camera_index=record.get("camera_index"),
                    system_type=record.get("system_type"),
                    retention_days=record.get("retention_days"),
                    manufacturer=record.get("manufacturer"),
                    latlon=latlon_value,
                    login_user=record.get("login_user"),
                    login_password=record.get("login_password"),
                    login_domain=record.get("login_domain"),
                    static_ip=record.get("static_ip"),
                    ip_port=record.get("ip_port"),
                    dvr_model=record.get("dvr_model"),
                    camera_model=record.get("camera_model"),
                    resolution=record.get("resolution"),
                    bandwidth=record.get("bandwidth"),
                    serial_number=record.get("serial_number"),
                    verification_code=record.get("verification_code"),
                    category=record.get("category"),
                    sharing_scope=record.get("sharing_scope", False),
                )

                cam.set_json("monitoring_modes", record.get("monitoring_modes", []))
                cam.set_json("storage_types", record.get("storage_types", []))
                cam.set_json("camera_types", record.get("camera_types", []))
                cam.set_json("form_factors", record.get("form_factors", []))
                cam.set_json("network_types", record.get("network_types", []))
                cam.set_json("install_areas", record.get("install_areas", []))
                cam.set_latlon_components()

                db.session.add(cam)
                success += 1
                batch_count += 1

                if batch_count >= batch_size:
                    db.session.commit()
                    batch_count = 0
            except (ValueError, TypeError, AttributeError) as exc:
                errors += 1
                error_msg = str(exc)
                camera_info = ""
                if record.get("system_type"):
                    camera_info = f" - Hệ thống: {record.get('system_type')}"
                if record.get("camera_index") is not None:
                    camera_info += f", Thứ tự: {record.get('camera_index')}"
                error_details.append({"row": idx, "error": error_msg, "info": camera_info})
                app.logger.warning("Validation error at record %s: %s", idx, exc)
                continue
            except (SQLAlchemyError, IntegrityError) as exc:
                errors += 1
                error_msg = f"Database error: {str(exc)}"
                app.logger.error(
                    "Database error importing camera record %s: %s",
                    idx,
                    exc,
                    exc_info=True,
                )
                db.session.rollback()
                camera_info = ""
                if record.get("system_type"):
                    camera_info = f" - Hệ thống: {record.get('system_type')}"
                if record.get("camera_index") is not None:
                    camera_info += f", Thứ tự: {record.get('camera_index')}"
                error_details.append({"row": idx, "error": error_msg, "info": camera_info})
                continue

        if batch_count > 0:
            db.session.commit()

        if user_id:
            log_audit(
                "import",
                "camera",
                None,
                {"success": success, "errors": errors, "file": os.path.basename(filepath)},
            )

    return {"success": success, "errors": errors, "details": error_details}
