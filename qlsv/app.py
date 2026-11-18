from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask import render_template

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-chi-dung-khi-phat-trien"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///qlsv.db"

db.init_app(app)

# Bước 3: Model Student
class Student(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    mssv: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    gpa: Mapped[float] = mapped_column(default=0.0)

    def __repr__(self):
        return f"<Student {self.mssv} {self.name}>"

# Bước 4: Tạo bảng
with app.app_context():
    db.create_all()

# Bước 5: Route thêm dữ liệu mẫu
@app.get("/them-mau")
def add_sample():
    total = db.session.scalar(
        db.select(func.count(Student.id))
    )
    if total > 0:
        return f"Đã có {total} sinh viên, không thêm nữa."

    an = Student(
        mssv="23T1020001", 
        name="Nguyễn Văn An", 
        gpa=8.5
    )

    before = an.id
    db.session.add(an)

    db.session.add_all([
        Student(mssv="23T1020002", name="Trần Thị Bình", gpa=6.8),
        Student(mssv="23T1020003", name="Lê Hoàng Cường", gpa=9.1),
        Student(mssv="23T1020004", name="Phạm Minh Dũng", gpa=4.5),
        Student(mssv="23T1020005", name="Hoàng Thu Hà", gpa=7.4),
    ])

    db.session.commit()

    return (
        f"Đã thêm 5 sinh viên. id của An: "
        f"trước commit = {before}, "
        f"sau commit = {an.id}"
    )
# Cấu hình trả về định dạng văn bản thuần (plain text) với UTF-8 để trình duyệt không hiểu nhầm thành HTML
TEXT = {"Content-Type": "text/plain; charset=utf-8"}

@app.get("/thu-truy-van")
def try_queries():
    # 1. Kiểm tra nếu chưa có dữ liệu thì tự động thêm 5 sinh viên mới
    if db.session.scalar(db.select(func.count(Student.id))) == 0:
        sample_students = [
            Student(mssv="23T1020006", name="Trần Quang Minh", gpa=8.8),
            Student(mssv="23T1020007", name="Nguyễn Thị Mai", gpa=7.9),
            Student(mssv="23T1020008", name="Đỗ Anh Tuấn", gpa=9.2),
            Student(mssv="23T1020009", name="Phạm Thanh Thảo", gpa=6.5),
            Student(mssv="23T1020010", name="Vũ Hoàng Long", gpa=8.1),
        ]
        db.session.add_all(sample_students)
        db.session.commit()

    # 2. Lấy dữ liệu cho 6 truy vấn
    # Dòng 1 & 2: Get theo ID
    get_3 = db.session.get(Student, 3)
    get_99 = db.session.get(Student, 99)

    # Dòng 3: Lấy tất cả sinh viên
    everyone = db.session.execute(db.select(Student)).scalars().all()

    # Dòng 4: Lọc GPA >= 8 và sắp xếp giảm dần
    stmt = db.select(Student).where(Student.gpa >= 8).order_by(Student.gpa.desc())
    good = db.session.execute(stmt).scalars().all()

    # Dòng 5: Lọc theo MSSV cụ thể (lấy sinh viên đầu tiên hoặc sinh viên vừa thêm)
    binh = db.session.scalar(db.select(Student).filter_by(mssv="23T1020007"))

    # Dòng 6: Đếm số lượng và tính điểm trung bình
    count = db.session.scalar(db.select(func.count(Student.id)))
    avg = db.session.scalar(db.select(func.avg(Student.gpa)))

    # 3. Truyền dữ liệu sang file template HTML
    return render_template(
        "thu_truy_van.html",
        get_3=get_3,
        get_99=get_99,
        everyone=everyone,
        good=good,
        binh=binh,
        count=count,
        avg=avg
    )