import base64
import binascii
import hashlib
import re
from uuid import uuid4

from flask import Blueprint, g, jsonify, request, send_file
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from io import BytesIO

from auth_api import authenticated, require_csrf
from database import Folder, Profile, ProfileImage, db, utc_now


records_api = Blueprint("records_api", __name__, url_prefix="/api")
MAX_PROFILES_PER_FOLDER = 50
MAX_FOLDERS = 100
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_FIELDS = {"front": "frontDataUrl", "back": "backDataUrl", "portrait": "portraitDataUrl"}
DATA_URL_PATTERN = re.compile(r"^data:(image/(?:jpeg|png));base64,([A-Za-z0-9+/]+={0,2})$")


def _error(code, message, status):
    return jsonify({"success": False, "code": code, "message": message}), status


def _identity(data):
    number = data.get("soCCCD") or data.get("soGiayTo") or ""
    value = re.sub(r"[^A-Z0-9]", "", str(number).upper())
    return value or None


def _parse_image(value, kind):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"Ảnh {kind} không hợp lệ.")
    match = DATA_URL_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"Ảnh {kind} phải là PNG hoặc JPEG hợp lệ.")
    mime, encoded = match.groups()
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"Ảnh {kind} không giải mã được.") from error
    signature = b"\x89PNG\r\n\x1a\n" if mime == "image/png" else b"\xff\xd8\xff"
    if not content or len(content) > MAX_IMAGE_BYTES or not content.startswith(signature):
        raise ValueError(f"Ảnh {kind} rỗng, vượt 10 MB hoặc sai định dạng.")
    return mime, content


def _images(profile, payload):
    existing = {image.kind: image for image in profile.images}
    for kind, field in IMAGE_FIELDS.items():
        if field not in payload:
            continue
        parsed = _parse_image(payload[field], kind)
        current = existing.get(kind)
        if parsed is None:
            if current:
                db.session.delete(current)
            continue
        mime, content = parsed
        if current is None:
            current = ProfileImage(profile_id=profile.id, kind=kind)
            db.session.add(current)
        current.mime_type = mime
        current.sha256 = hashlib.sha256(content).hexdigest()
        current.image_data = content


def _profile_payload(profile, include_scans=False):
    payload = dict(profile.data or {})
    payload.update(
        {
            "id": profile.id,
            "folderId": profile.folder_id,
            "version": profile.version,
            "createdAt": profile.created_at.isoformat() if profile.created_at else None,
            "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
        }
    )
    images = {image.kind: image for image in profile.images}
    for kind, field in IMAGE_FIELDS.items():
        image = images.get(kind)
        if image and (include_scans or kind == "portrait"):
            payload[field] = f"data:{image.mime_type};base64,{base64.b64encode(image.image_data).decode('ascii')}"
        else:
            payload[field] = None
    return payload


def _folder_payload(folder):
    return {
        "id": folder.id,
        "name": folder.name,
        "version": folder.version,
        "createdAt": folder.created_at.isoformat(),
        "updatedAt": folder.updated_at.isoformat(),
        "profileCount": len(folder.profiles),
    }


def _check_folder_capacity(folder_id):
    db.session.query(Folder.id).order_by(Folder.id).with_for_update().first()
    count = db.session.query(func.count(Profile.id)).filter_by(folder_id=folder_id).scalar()
    return count >= MAX_PROFILES_PER_FOLDER


@records_api.get("/folders")
@authenticated
def list_folders():
    folders = db.session.query(Folder).order_by(Folder.created_at, Folder.id).all()
    return jsonify({"success": True, "folders": [_folder_payload(folder) for folder in folders]}), 200


@records_api.post("/folders")
@authenticated
def create_folder():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    payload = request.get_json(silent=True)
    name = payload.get("name", "").strip() if isinstance(payload, dict) and isinstance(payload.get("name"), str) else ""
    if not name or len(name) > 100:
        return _error("INVALID_FOLDER", "Tên thư mục cần từ 1 đến 100 ký tự.", 400)
    db.session.query(Folder.id).order_by(Folder.id).with_for_update().first()
    folder_count = db.session.query(func.count(Folder.id)).scalar()
    if folder_count >= MAX_FOLDERS:
        return _error("FOLDER_CAPACITY", f"Hệ thống chỉ lưu tối đa {MAX_FOLDERS} thư mục.", 409)
    folder = Folder(id=str(uuid4()), name=name)
    db.session.add(folder)
    db.session.commit()
    return jsonify({"success": True, "folder": _folder_payload(folder)}), 201


@records_api.get("/folders/<string:folder_id>")
@authenticated
def get_folder(folder_id):
    folder = db.session.get(Folder, folder_id)
    if folder is None:
        return _error("NOT_FOUND", "Không tìm thấy thư mục.", 404)
    return jsonify({"success": True, "folder": _folder_payload(folder)}), 200


@records_api.patch("/folders/<string:folder_id>")
@authenticated
def rename_folder(folder_id):
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    folder = db.session.get(Folder, folder_id)
    payload = request.get_json(silent=True)
    if folder is None:
        return _error("NOT_FOUND", "Không tìm thấy thư mục.", 404)
    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
        return _error("INVALID_FOLDER", "Tên thư mục không hợp lệ.", 400)
    version = request.headers.get("If-Match")
    if version != str(folder.version):
        return _error("VERSION_CONFLICT", "Thư mục đã thay đổi. Hãy tải lại trước khi lưu.", 409)
    name = payload["name"].strip()
    if not name or len(name) > 100:
        return _error("INVALID_FOLDER", "Tên thư mục cần từ 1 đến 100 ký tự.", 400)
    result = db.session.execute(
        update(Folder).where(Folder.id == folder_id, Folder.version == int(version))
        .values(name=name, version=Folder.version + 1, updated_at=utc_now())
    )
    if result.rowcount != 1:
        db.session.rollback()
        return _error("VERSION_CONFLICT", "Thư mục đã thay đổi. Hãy tải lại trước khi lưu.", 409)
    db.session.commit()
    return jsonify({"success": True, "folder": _folder_payload(db.session.get(Folder, folder_id))}), 200


@records_api.delete("/folders/<string:folder_id>")
@authenticated
def delete_folder(folder_id):
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    folder = db.session.get(Folder, folder_id)
    if folder is None:
        return _error("NOT_FOUND", "Không tìm thấy thư mục.", 404)
    db.session.delete(folder)
    db.session.commit()
    return jsonify({"success": True}), 200


@records_api.get("/folders/<string:folder_id>/profiles")
@authenticated
def list_profiles(folder_id):
    if db.session.get(Folder, folder_id) is None:
        return _error("NOT_FOUND", "Không tìm thấy thư mục.", 404)
    profiles = db.session.query(Profile).filter_by(folder_id=folder_id).order_by(Profile.created_at, Profile.id).all()
    return jsonify({"success": True, "profiles": [_profile_payload(item) for item in profiles]}), 200


@records_api.post("/folders/<string:folder_id>/profiles")
@authenticated
def create_profile(folder_id):
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    folder = db.session.get(Folder, folder_id)
    payload = request.get_json(silent=True)
    if folder is None:
        return _error("NOT_FOUND", "Không tìm thấy thư mục.", 404)
    if not isinstance(payload, dict):
        return _error("INVALID_PROFILE", "Dữ liệu hồ sơ không hợp lệ.", 400)
    if not isinstance(payload.get("hoTen"), str) or not payload["hoTen"].strip():
        return _error("INVALID_PROFILE", "Họ và tên là bắt buộc.", 400)
    if _check_folder_capacity(folder_id):
        return _error("FOLDER_CAPACITY", f"Mỗi thư mục chỉ lưu tối đa {MAX_PROFILES_PER_FOLDER} hồ sơ.", 409)
    profile_id = str(payload.get("id") or uuid4())
    if db.session.get(Profile, profile_id):
        return _error("PROFILE_EXISTS", "Mã hồ sơ đã tồn tại.", 409)
    identity = _identity(payload)
    if identity and db.session.query(Profile.id).filter_by(identity_number_norm=identity).first():
        return _error("IDENTITY_EXISTS", "Số giấy tờ đã tồn tại.", 409)
    reserved = {"id", "folderId", "version", "createdAt", "updatedAt", *IMAGE_FIELDS.values()}
    profile = Profile(
        id=profile_id, folder_id=folder_id,
        data={key: value for key, value in payload.items() if key not in reserved},
        identity_number_norm=identity, created_by_id=g.current_user.id,
    )
    db.session.add(profile)
    try:
        _images(profile, payload)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return _error("INVALID_IMAGE", str(error), 400)
    except IntegrityError:
        db.session.rollback()
        return _error("IDENTITY_EXISTS", "Số giấy tờ hoặc mã hồ sơ đã tồn tại.", 409)
    return jsonify({"success": True, "profile": _profile_payload(profile, True)}), 201


@records_api.post("/folders/<string:folder_id>/profiles/delete")
@authenticated
def delete_folder_profiles(folder_id):
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    folder = db.session.get(Folder, folder_id)
    if folder is None:
        return _error("NOT_FOUND", "Không tìm thấy thư mục.", 404)
    payload = request.get_json(silent=True)
    ids = payload.get("ids") if isinstance(payload, dict) else None
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        return _error("INVALID_REQUEST", "Danh sách mã hồ sơ không hợp lệ.", 400)
    if ids:
        db.session.query(Profile).filter(
            Profile.folder_id == folder_id, Profile.id.in_(ids)
        ).delete(synchronize_session=False)
        db.session.commit()
    return jsonify({"success": True}), 200


@records_api.get("/profiles/<string:profile_id>")
@authenticated
def get_profile(profile_id):
    profile = db.session.get(Profile, profile_id)
    if profile is None:
        return _error("NOT_FOUND", "Không tìm thấy hồ sơ.", 404)
    return jsonify({"success": True, "profile": _profile_payload(profile, True)}), 200


@records_api.patch("/profiles/<string:profile_id>")
@authenticated
def update_profile(profile_id):
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    profile = db.session.get(Profile, profile_id)
    payload = request.get_json(silent=True)
    if profile is None:
        return _error("NOT_FOUND", "Không tìm thấy hồ sơ.", 404)
    if not isinstance(payload, dict) or not isinstance(payload.get("hoTen"), str) or not payload["hoTen"].strip():
        return _error("INVALID_PROFILE", "Họ và tên là bắt buộc.", 400)
    version = request.headers.get("If-Match")
    if version != str(profile.version):
        return _error("VERSION_CONFLICT", "Hồ sơ đã được người khác cập nhật. Hãy tải lại trước khi lưu.", 409)
    identity = _identity(payload)
    duplicate = db.session.query(Profile.id).filter(
        Profile.identity_number_norm == identity, Profile.id != profile.id
    ).first() if identity else None
    if duplicate:
        return _error("IDENTITY_EXISTS", "Số giấy tờ đã tồn tại.", 409)
    reserved = {"id", "folderId", "version", "createdAt", "updatedAt", *IMAGE_FIELDS.values()}
    data = {key: value for key, value in payload.items() if key not in reserved}
    try:
        _images(profile, payload)
        result = db.session.execute(
            update(Profile)
            .where(Profile.id == profile_id, Profile.version == int(version))
            .values(
                data=data,
                identity_number_norm=identity,
                updated_by_id=g.current_user.id,
                version=Profile.version + 1,
                updated_at=utc_now(),
            )
        )
        if result.rowcount != 1:
            db.session.rollback()
            return _error("VERSION_CONFLICT", "Hồ sơ đã được người khác cập nhật. Hãy tải lại trước khi lưu.", 409)
        db.session.expire(profile)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return _error("INVALID_IMAGE", str(error), 400)
    except IntegrityError:
        db.session.rollback()
        return _error("IDENTITY_EXISTS", "Số giấy tờ đã tồn tại.", 409)
    return jsonify({"success": True, "profile": _profile_payload(db.session.get(Profile, profile_id), True)}), 200


@records_api.post("/profiles/delete")
@authenticated
def delete_profiles():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    payload = request.get_json(silent=True)
    ids = payload.get("ids") if isinstance(payload, dict) else None
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        return _error("INVALID_REQUEST", "Danh sách mã hồ sơ không hợp lệ.", 400)
    db.session.query(Profile).filter(Profile.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True}), 200


@records_api.delete("/profiles/<string:profile_id>")
@authenticated
def delete_profile(profile_id):
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    profile = db.session.get(Profile, profile_id)
    if profile is None:
        return _error("NOT_FOUND", "Không tìm thấy hồ sơ.", 404)
    db.session.delete(profile)
    db.session.commit()
    return jsonify({"success": True}), 200


@records_api.get("/profiles/<string:profile_id>/images/<string:kind>")
@authenticated
def get_profile_image(profile_id, kind):
    image = db.session.query(ProfileImage).filter_by(profile_id=profile_id, kind=kind).one_or_none()
    if image is None:
        return _error("NOT_FOUND", "Không tìm thấy ảnh.", 404)
    return send_file(BytesIO(image.image_data), mimetype=image.mime_type, max_age=0)
