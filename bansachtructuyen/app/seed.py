from sqlalchemy import func, select

from app.extensions import db
from app.models import Book, Category


def seed_sample_data() -> bool:
    """Thêm dữ liệu mẫu nếu database trống. Trả về True nếu đã seed."""
    total = db.session.scalar(select(func.count(Category.id)))
    if total and total > 0:
        return False

    categories = {
        "Lập trình": Category(name="Lập trình", description="Ngôn ngữ và framework"),
        "Cơ sở dữ liệu": Category(name="Cơ sở dữ liệu", description="CSDL và thiết kế"),
        "Công cụ": Category(name="Công cụ", description="Công cụ phát triển"),
        "Mạng": Category(name="Mạng", description="Mạng máy tính"),
        "Kỹ năng lập trình": Category(
            name="Kỹ năng lập trình", description="Best practices"
        ),
        "Thiết kế": Category(name="Thiết kế", description="UI/UX và thiết kế phần mềm"),
    }
    db.session.add_all(categories.values())
    db.session.flush()

    books = [
        Book(
            title="Lập trình Python cơ bản",
            author="Nguyễn Văn A",
            publisher="NXB Đại học Huế",
            year=2024,
            price=95_000,
            stock=30,
            description="Giáo trình nhập môn Python dành cho sinh viên.",
            category_id=categories["Lập trình"].id,
        ),
        Book(
            title="Giáo trình Flask",
            author="Trần Thị B",
            publisher="NXB Giáo dục",
            year=2023,
            price=120_000,
            stock=20,
            description="Xây dựng ứng dụng web với Flask.",
            category_id=categories["Lập trình"].id,
        ),
        Book(
            title="Cơ sở dữ liệu",
            author="Lê Văn C",
            publisher="NXB Khoa học",
            year=2022,
            price=85_000,
            stock=0,
            description="Các khái niệm cơ bản về hệ quản trị CSDL.",
            category_id=categories["Cơ sở dữ liệu"].id,
        ),
        Book(
            title="Pro Git",
            author="Scott Chacon",
            publisher="Apress",
            year=2014,
            price=150_000,
            stock=15,
            description="Hướng dẫn sử dụng Git chuyên sâu.",
            category_id=categories["Công cụ"].id,
        ),
        Book(
            title="Mạng máy tính",
            author="Phạm Minh D",
            publisher="NXB Thông tin",
            year=2021,
            price=110_000,
            stock=12,
            description="Kiến trúc và giao thức mạng máy tính.",
            category_id=categories["Mạng"].id,
        ),
        Book(
            title="Clean Code",
            author="Robert C. Martin",
            publisher="Prentice Hall",
            year=2008,
            price=180_000,
            stock=5,
            description="A Handbook of Agile Software Craftsmanship.",
            category_id=categories["Kỹ năng lập trình"].id,
        ),
    ]
    db.session.add_all(books)
    db.session.commit()
    return True
