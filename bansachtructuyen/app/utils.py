import os
import secrets
from datetime import datetime

from flask import current_app
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def format_vnd(amount: int | None) -> str:
    if amount is None:
        return "0 đ"
    return f"{amount:,}".replace(",", ".") + " đ"


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_cover_image(file: FileStorage) -> str | None:
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError("Chỉ chấp nhận ảnh JPG, PNG, WEBP.")

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > current_app.config["MAX_CONTENT_LENGTH"]:
        raise ValueError("Ảnh không được vượt quá 2 MB.")

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{secrets.token_hex(8)}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, filename)

    try:
        image = Image.open(file.stream)
        image.verify()
        file.stream.seek(0)
        image = Image.open(file.stream)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(path)
    except Exception as exc:
        raise ValueError("File ảnh không hợp lệ.") from exc

    return filename


def delete_cover_image(filename: str | None) -> None:
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(filename))
    if os.path.isfile(path):
        os.remove(path)


def current_year() -> int:
    return datetime.now().year


def status_badge_class(status: str) -> str:
    mapping = {
        "Chờ xác nhận": "warning",
        "Đang giao": "primary",
        "Hoàn tất": "success",
        "Đã huỷ": "secondary",
    }
    return mapping.get(status, "secondary")
