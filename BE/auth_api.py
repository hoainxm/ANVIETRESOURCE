import secrets
from functools import wraps
from uuid import uuid4

from flask import Blueprint, g, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database import User, db


auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")


def authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if (
            user is None
            or not user.is_active
            or session.get("session_version") != user.session_version
        ):
            session.clear()
            return jsonify(
                {"success": False, "code": "AUTH_REQUIRED", "message": "Vui lòng đăng nhập."}
            ), 401
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def admin_only(view):
    @wraps(view)
    @authenticated
    def wrapped(*args, **kwargs):
        if g.current_user.role != "admin":
            return jsonify(
                {"success": False, "code": "FORBIDDEN", "message": "Bạn không có quyền thực hiện thao tác này."}
            ), 403
        return view(*args, **kwargs)

    return wrapped


def require_csrf():
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token", "")
    if not expected or not secrets.compare_digest(expected, supplied):
        return jsonify(
            {"success": False, "code": "CSRF_INVALID", "message": "Phiên bảo mật không hợp lệ. Hãy tải lại trang."}
        ), 403
    return None


@auth_api.get("/session")
def get_session():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if (
        user is None
        or not user.is_active
        or session.get("session_version") != user.session_version
    ):
        session.clear()
        return jsonify({"success": True, "authenticated": False}), 200
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify(
        {
            "success": True,
            "authenticated": True,
            "csrfToken": session["csrf_token"],
            "user": {"id": user.id, "email": user.email, "role": user.role},
        }
    ), 200


@auth_api.post("/login")
def login():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "code": "INVALID_REQUEST", "message": "Thông tin đăng nhập không hợp lệ."}), 400
    email = str(payload.get("email", "")).strip().casefold()
    password = payload.get("password")
    if not email or not isinstance(password, str) or not password:
        return jsonify({"success": False, "code": "INVALID_CREDENTIALS", "message": "Vui lòng nhập email và mật khẩu."}), 400
    user = db.session.query(User).filter_by(email=email).one_or_none()
    if user is None or not user.is_active or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "code": "INVALID_CREDENTIALS", "message": "Email hoặc mật khẩu không đúng."}), 401
    session.clear()
    session["user_id"] = user.id
    session["session_version"] = user.session_version
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify(
        {
            "success": True,
            "authenticated": True,
            "csrfToken": session["csrf_token"],
            "user": {"id": user.id, "email": user.email, "role": user.role},
        }
    ), 200


@auth_api.post("/logout")
@authenticated
def logout():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    user = db.session.get(User, session.get("user_id"))
    if user:
        user.session_version += 1
        db.session.commit()
    session.clear()
    return jsonify({"success": True}), 200


def create_account(email, password, role="admin"):
    normalized_email = email.strip().casefold()
    if (
        not normalized_email
        or len(normalized_email) > 320
        or len(password) < 12
        or role not in {"admin", "employee"}
    ):
        raise ValueError("Email, vai trò hoặc mật khẩu không hợp lệ; mật khẩu cần ít nhất 12 ký tự.")
    user = User(
        id=str(uuid4()),
        email=normalized_email,
        password_hash=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ValueError("Email này đã được sử dụng.") from error
    return user


@auth_api.post("/users")
@admin_only
def create_user():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "code": "INVALID_REQUEST", "message": "Thông tin tài khoản không hợp lệ."}), 400
    email = str(payload.get("email", "")).strip()
    password = payload.get("password")
    role = payload.get("role", "employee")
    if not isinstance(password, str):
        return jsonify({"success": False, "code": "INVALID_USER", "message": "Mật khẩu không hợp lệ."}), 400
    try:
        user = create_account(email, password, role)
    except ValueError as error:
        code = "USER_EXISTS" if "đã được sử dụng" in str(error) else "INVALID_USER"
        return jsonify({"success": False, "code": code, "message": str(error)}), 409 if code == "USER_EXISTS" else 400
    return jsonify(
        {"success": True, "user": {"id": user.id, "email": user.email, "role": user.role}}
    ), 201
