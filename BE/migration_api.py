from collections import Counter

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from auth_api import admin_only, require_csrf
from database import Folder, Profile, ProfileImage, db
from records_api import (
    IMAGE_FIELDS,
    MAX_FOLDERS,
    MAX_PROFILES_PER_FOLDER,
    _identity,
    _parse_image,
)


migration_api = Blueprint("migration_api", __name__, url_prefix="/api/admin/import")
RESERVED_FIELDS = {
    "id", "folderId", "version", "createdAt", "updatedAt", *IMAGE_FIELDS.values()
}


def _validate(bundle):
    issues = []
    if not isinstance(bundle, dict) or bundle.get("version") != 1:
        return [{"record": "bundle", "index": 0, "message": "Tệp sao lưu không đúng định dạng."}]
    folders = bundle.get("folders")
    profiles = bundle.get("profiles")
    if not isinstance(folders, list) or not isinstance(profiles, list):
        return [{"record": "bundle", "index": 0, "message": "Tệp cần có danh sách folders và profiles."}]

    if db.session.query(func.count(Folder.id)).scalar() + len(folders) > MAX_FOLDERS:
        issues.append(
            {
                "record": "bundle",
                "index": 0,
                "message": f"Hệ thống chỉ lưu tối đa {MAX_FOLDERS} thư mục.",
            }
        )

    folder_ids = set()
    for index, folder in enumerate(folders, 1):
        if not isinstance(folder, dict):
            issues.append({"record": "folder", "index": index, "message": "Thư mục không hợp lệ."})
            continue
        folder_id, name = folder.get("id"), folder.get("name")
        if not isinstance(folder_id, str) or not folder_id or len(folder_id) > 80:
            issues.append({"record": "folder", "index": index, "message": "Mã thư mục không hợp lệ."})
            continue
        if folder_id in folder_ids or db.session.get(Folder, folder_id):
            issues.append({"record": "folder", "index": index, "message": "Mã thư mục bị trùng hoặc đã tồn tại."})
        folder_ids.add(folder_id)
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            issues.append({"record": "folder", "index": index, "message": "Tên thư mục không hợp lệ."})

    counts = Counter()
    profile_ids = set()
    identity_ids = set()
    for index, profile in enumerate(profiles, 1):
        if not isinstance(profile, dict):
            issues.append({"record": "profile", "index": index, "message": "Hồ sơ không hợp lệ."})
            continue
        profile_id = profile.get("id")
        folder_id = profile.get("folderId")
        if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 80:
            issues.append({"record": "profile", "index": index, "message": "Mã hồ sơ không hợp lệ."})
            continue
        if profile_id in profile_ids or db.session.get(Profile, profile_id):
            issues.append({"record": "profile", "index": index, "message": "Mã hồ sơ bị trùng hoặc đã tồn tại."})
        profile_ids.add(profile_id)
        if not isinstance(profile.get("hoTen"), str) or not profile["hoTen"].strip():
            issues.append({"record": "profile", "index": index, "message": "Họ và tên là bắt buộc."})
        if not isinstance(folder_id, str) or folder_id not in folder_ids:
            issues.append({"record": "profile", "index": index, "message": "Không tìm thấy thư mục tương ứng."})
        else:
            counts[folder_id] += 1
        identity = _identity(profile)
        if identity:
            if identity in identity_ids or db.session.query(Profile.id).filter_by(identity_number_norm=identity).first():
                issues.append({"record": "profile", "index": index, "message": "Số giấy tờ bị trùng hoặc đã tồn tại."})
            identity_ids.add(identity)
        for kind, field in IMAGE_FIELDS.items():
            try:
                _parse_image(profile.get(field), kind)
            except ValueError as error:
                issues.append({"record": "profile", "index": index, "message": str(error)})
    for folder_id, count in counts.items():
        if count > MAX_PROFILES_PER_FOLDER:
            issues.append({"record": "folder", "index": 0, "message": f"Thư mục vượt giới hạn {MAX_PROFILES_PER_FOLDER} hồ sơ."})
    return issues


@migration_api.post("/preview")
@admin_only
def preview_import():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    bundle = request.get_json(silent=True)
    issues = _validate(bundle)
    folders = bundle.get("folders", []) if isinstance(bundle, dict) else []
    profiles = bundle.get("profiles", []) if isinstance(bundle, dict) else []
    images = sum(
        bool(profile.get(field))
        for profile in profiles if isinstance(profile, dict)
        for field in IMAGE_FIELDS.values()
    )
    return jsonify(
        {
            "success": True,
            "canImport": not issues,
            "folderCount": len(folders) if isinstance(folders, list) else 0,
            "profileCount": len(profiles) if isinstance(profiles, list) else 0,
            "imageCount": images,
            "issues": issues,
        }
    ), 200


@migration_api.post("")
@admin_only
def import_bundle():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error
    bundle = request.get_json(silent=True)
    issues = _validate(bundle)
    if issues:
        return jsonify({"success": False, "code": "IMPORT_VALIDATION_FAILED", "issues": issues}), 400
    folders = bundle["folders"]
    profiles = bundle["profiles"]
    try:
        for item in folders:
            db.session.add(Folder(id=item["id"], name=item["name"].strip()))
        db.session.flush()
        for item in profiles:
            profile = Profile(
                id=item["id"],
                folder_id=item["folderId"],
                data={key: value for key, value in item.items() if key not in RESERVED_FIELDS},
                identity_number_norm=_identity(item),
                created_by_id=None,
            )
            db.session.add(profile)
            for kind, field in IMAGE_FIELDS.items():
                parsed = _parse_image(item.get(field), kind)
                if parsed is None:
                    continue
                mime_type, image_data = parsed
                import hashlib
                db.session.add(
                    ProfileImage(
                        profile_id=profile.id, kind=kind, mime_type=mime_type,
                        sha256=hashlib.sha256(image_data).hexdigest(),
                        image_data=image_data,
                    )
                )
        db.session.commit()
    except (ValueError, IntegrityError) as error:
        db.session.rollback()
        return jsonify(
            {"success": False, "code": "IMPORT_FAILED", "message": "Không thể nhập dữ liệu; hãy kiểm tra trùng lặp và thử lại."}
        ), 409
    return jsonify(
        {"success": True, "folderCount": len(folders), "profileCount": len(profiles)}
    ), 201
