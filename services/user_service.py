from datetime import datetime

from werkzeug.security import generate_password_hash

from models import db, User
from security_utils import validate_password


def create_user(
    username,
    password,
    role,
    config,
    require_password_change=True,
):
    is_valid, error_msg = validate_password(
        password,
        min_length=config.get("PASSWORD_MIN_LENGTH", 8),
        require_uppercase=config.get("PASSWORD_REQUIRE_UPPERCASE", True),
        require_lowercase=config.get("PASSWORD_REQUIRE_LOWERCASE", True),
        require_number=config.get("PASSWORD_REQUIRE_NUMBER", True),
        require_special=config.get("PASSWORD_REQUIRE_SPECIAL", True),
    )

    if not is_valid:
        return None, error_msg

    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role,
        password_changed_at=datetime.utcnow(),
        require_password_change=require_password_change,
    )
    db.session.add(user)
    db.session.commit()
    return user, None
