import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-chi-dung-khi-phat-trien")
    _db_path = os.path.join(BASE_DIR, "instance", "bansach.db").replace("\\", "/")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + _db_path,
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    SHIPPING_FEE = 20_000
    FREE_SHIPPING_THRESHOLD = 200_000
    LOW_STOCK_THRESHOLD = 5
