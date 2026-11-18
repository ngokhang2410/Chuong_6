import re
from datetime import datetime

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    IntegerField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from app.extensions import db
from app.models import Book, Category, PAYMENT_BANK, PAYMENT_COD


class CheckoutForm(FlaskForm):
    customer_name = StringField(
        "Họ tên",
        validators=[DataRequired(message="Vui lòng nhập họ tên."), Length(max=100)],
    )
    phone = StringField(
        "Số điện thoại",
        validators=[DataRequired(message="Vui lòng nhập số điện thoại."), Length(max=15)],
    )
    email = StringField(
        "Email",
        validators=[Optional(), Email(message="Email không hợp lệ."), Length(max=120)],
    )
    address = TextAreaField(
        "Địa chỉ giao hàng",
        validators=[DataRequired(message="Vui lòng nhập địa chỉ."), Length(max=500)],
    )
    note = TextAreaField("Ghi chú", validators=[Optional(), Length(max=500)])
    payment_method = RadioField(
        "Thanh toán",
        choices=[
            (PAYMENT_COD, PAYMENT_COD),
            (PAYMENT_BANK, PAYMENT_BANK),
        ],
        default=PAYMENT_COD,
        validators=[DataRequired()],
    )
    submit = SubmitField("Xác nhận đặt hàng")

    def validate_phone(self, field):
        phone = field.data.strip() if field.data else ""
        if not re.fullmatch(r"0\d{9}", phone):
            raise ValidationError("Số điện thoại gồm 10 chữ số và bắt đầu bằng 0.")


class BookForm(FlaskForm):
    title = StringField(
        "Tên sách",
        validators=[DataRequired(message="Vui lòng nhập tên sách."), Length(max=200)],
    )
    author = StringField(
        "Tác giả",
        validators=[DataRequired(message="Vui lòng nhập tác giả."), Length(max=100)],
    )
    category_id = SelectField(
        "Danh mục",
        coerce=int,
        validators=[DataRequired(message="Vui lòng chọn danh mục.")],
    )
    publisher = StringField("Nhà xuất bản", validators=[Optional(), Length(max=150)])
    year = IntegerField(
        "Năm xuất bản",
        validators=[Optional()],
    )
    price = IntegerField(
        "Giá (đồng)",
        validators=[
            DataRequired(message="Vui lòng nhập giá."),
            NumberRange(min=1000, message="Giá phải ≥ 1.000."),
        ],
    )
    stock = IntegerField(
        "Tồn kho",
        validators=[
            InputRequired(message="Vui lòng nhập tồn kho."),
            NumberRange(min=0, message="Tồn kho không âm."),
        ],
    )
    description = TextAreaField("Mô tả", validators=[Optional()])
    cover_image = FileField(
        "Ảnh bìa",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Chỉ JPG, PNG, WEBP."),
        ],
    )
    submit = SubmitField("Lưu")

    def __init__(self, book_id: int | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book_id = book_id
        categories = db.session.execute(
            db.select(Category).order_by(Category.name)
        ).scalars().all()
        self.category_id.choices = [(c.id, c.name) for c in categories]

    def validate_title(self, field):
        title = field.data.strip() if field.data else ""
        stmt = db.select(Book).where(db.func.lower(Book.title) == title.lower())
        if self.book_id:
            stmt = stmt.where(Book.id != self.book_id)
        exists = db.session.scalar(stmt)
        if exists:
            raise ValidationError("Tên sách đã tồn tại.")

    def validate_year(self, field):
        if field.data is None:
            return
        year_now = datetime.now().year
        if field.data < 1900 or field.data > year_now:
            raise ValidationError(f"Năm xuất bản phải từ 1900 đến {year_now}.")


class CategoryForm(FlaskForm):
    name = StringField(
        "Tên",
        validators=[DataRequired(message="Vui lòng nhập tên danh mục."), Length(max=100)],
    )
    description = TextAreaField("Mô tả", validators=[Optional()])
    submit = SubmitField("+ Thêm")

    def __init__(self, category_id: int | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id = category_id
        if category_id:
            self.submit.label.text = "Cập nhật"

    def validate_name(self, field):
        name = field.data.strip() if field.data else ""
        stmt = db.select(Category).where(db.func.lower(Category.name) == name.lower())
        if self.category_id:
            stmt = stmt.where(Category.id != self.category_id)
        exists = db.session.scalar(stmt)
        if exists:
            raise ValidationError("Danh mục đã tồn tại.")


class OrderStatusForm(FlaskForm):
    status = SelectField("Chuyển sang", validators=[DataRequired()])
    submit = SubmitField("Cập nhật")


class CSRFOnlyForm(FlaskForm):
    """Form chỉ để lấy CSRF token cho các nút POST đơn giản."""
    pass
