# Nhà sách Sông Hương (bansachtructuyen)

Bài tập tổng hợp: trang bán hàng + trang quản trị.

## Công nghệ

- Giỏ hàng: Session
- Form: Flask-WTF
- CSDL: SQLAlchemy + Flask-Migrate
- Giao diện: Jinja2 + Bootstrap 5

## Cài đặt & chạy

```bash
cd chuong_06/bansachtructuyen
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python run.py
```

Mở: http://127.0.0.1:5000

Dữ liệu mẫu (6 danh mục, 6 sách) được seed tự động lần đầu.

## Migration (tuỳ chọn)

```bash
flask --app run.py db init
flask --app run.py db migrate -m "init"
flask --app run.py db upgrade
```

## Routes chính

**Bán hàng:** `/books`, `/books/<id>`, `/cart`, `/checkout`, `/orders/<id>`

**Quản trị:** `/admin`, `/admin/books`, `/admin/categories`, `/admin/orders`
