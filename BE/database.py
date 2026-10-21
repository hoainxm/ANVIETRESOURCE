from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB


db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(320), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="employee")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'employee')", name="ck_users_role"),
    )


class Folder(db.Model):
    __tablename__ = "folders"

    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    profiles = db.relationship(
        "Profile", back_populates="folder", cascade="all, delete-orphan"
    )


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.String(80), primary_key=True)
    folder_id = db.Column(
        db.String(80), db.ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    data = db.Column(db.JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    identity_number_norm = db.Column(db.String(32), nullable=True, unique=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    created_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    updated_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    folder = db.relationship("Folder", back_populates="profiles")
    images = db.relationship(
        "ProfileImage", back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileImage(db.Model):
    __tablename__ = "profile_images"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(
        db.String(80), db.ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    kind = db.Column(db.String(16), nullable=False)
    mime_type = db.Column(db.String(32), nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    profile = db.relationship("Profile", back_populates="images")

    __table_args__ = (
        UniqueConstraint("profile_id", "kind", name="uq_profile_images_profile_kind"),
        CheckConstraint(
            "kind IN ('front', 'back', 'portrait')", name="ck_profile_images_kind"
        ),
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png')",
            name="ck_profile_images_mime_type",
        ),
    )
