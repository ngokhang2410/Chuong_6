from datetime import datetime, timedelta

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.admin import admin_bp
from app.extensions import db
from app.forms import BookForm, CategoryForm, CSRFOnlyForm, OrderStatusForm
from app.models import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_PENDING,
    ORDER_STATUSES,
    STATUS_TRANSITIONS,
    Book,
    Category,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from app.utils import delete_cover_image, save_cover_image


def _pending_count() -> int:
    return (
        db.session.scalar(
            select(func.count(Order.id)).where(Order.status == ORDER_STATUS_PENDING)
        )
        or 0
    )


@admin_bp.context_processor
def inject_admin_globals():
    return {"pending_orders_count": _pending_count()}


@admin_bp.get("/")
def dashboard():
    total_books = db.session.scalar(select(func.count(Book.id))) or 0
    pending_orders = _pending_count()

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    month_revenue = (
        db.session.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.status == ORDER_STATUS_COMPLETED,
                Order.created_at >= month_start,
            )
        )
        or 0
    )

    low_stock_count = (
        db.session.scalar(select(func.count(Book.id)).where(Book.stock <= 5)) or 0
    )

    recent_orders = db.session.execute(
        select(Order).order_by(Order.created_at.desc()).limit(5)
    ).scalars().all()

    low_stock_books = db.session.execute(
        select(Book).where(Book.stock <= 5).order_by(Book.stock.asc(), Book.title)
    ).scalars().all()

    # Doanh thu 7 ngày (đơn hoàn tất)
    days = []
    revenues = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        revenue = (
            db.session.scalar(
                select(func.coalesce(func.sum(Order.total), 0)).where(
                    Order.status == ORDER_STATUS_COMPLETED,
                    Order.created_at >= day_start,
                    Order.created_at < day_end,
                )
            )
            or 0
        )
        days.append(day.strftime("%d/%m"))
        revenues.append(int(revenue))

    max_revenue = max(revenues) if revenues else 1

    return render_template(
        "admin/dashboard.html",
        total_books=total_books,
        pending_orders=pending_orders,
        month_revenue=month_revenue,
        low_stock_count=low_stock_count,
        recent_orders=recent_orders,
        low_stock_books=low_stock_books,
        chart_days=days,
        chart_revenues=revenues,
        chart_max=max_revenue or 1,
        month_label=now.strftime("%m"),
    )


# ---------- Sách ----------


@admin_bp.get("/books")
def books_list():
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category_id", type=int)
    stock_filter = request.args.get("stock") or ""
    page = request.args.get("page", 1, type=int)
    per_page = 5

    stmt = select(Book).options(joinedload(Book.category)).order_by(Book.created_at.desc())

    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Book.title.ilike(like), Book.author.ilike(like)))
    if category_id:
        stmt = stmt.where(Book.category_id == category_id)
    if stock_filter == "in_stock":
        stmt = stmt.where(Book.stock > 5)
    elif stock_filter == "low":
        stmt = stmt.where(Book.stock > 0, Book.stock <= 5)
    elif stock_filter == "out":
        stmt = stmt.where(Book.stock == 0)

    total = db.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    books = db.session.execute(
        stmt.offset((page - 1) * per_page).limit(per_page)
    ).scalars().unique().all()

    # Sách đã có trong đơn hàng → không xoá được
    ordered_ids = set(
        db.session.execute(select(OrderItem.book_id).distinct()).scalars().all()
    )

    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()
    form = CSRFOnlyForm()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "admin/books_list.html",
        books=books,
        categories=categories,
        ordered_ids=ordered_ids,
        q=q,
        category_id=category_id,
        stock_filter=stock_filter,
        page=page,
        total=total,
        total_pages=total_pages,
        per_page=per_page,
        form=form,
    )


@admin_bp.route("/books/new", methods=["GET", "POST"])
def books_create():
    form = BookForm()
    if not form.category_id.choices:
        flash("Cần tạo ít nhất một danh mục trước khi thêm sách.", "warning")
        return redirect(url_for("admin.categories_list"))

    if form.validate_on_submit():
        cover = None
        if form.cover_image.data:
            try:
                cover = save_cover_image(form.cover_image.data)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("admin/book_form.html", form=form, book=None)

        book = Book(
            title=form.title.data.strip(),
            author=form.author.data.strip(),
            publisher=(form.publisher.data or "").strip() or None,
            year=form.year.data,
            price=form.price.data,
            stock=form.stock.data,
            description=(form.description.data or "").strip() or None,
            cover_image=cover,
            category_id=form.category_id.data,
        )
        db.session.add(book)
        db.session.commit()
        flash("Đã thêm sách.", "success")
        return redirect(url_for("admin.books_list"))

    return render_template("admin/book_form.html", form=form, book=None)


@admin_bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def books_edit(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    form = BookForm(book_id=book.id, obj=book)
    if request.method == "GET":
        form.category_id.data = book.category_id

    if form.validate_on_submit():
        if form.cover_image.data:
            try:
                new_cover = save_cover_image(form.cover_image.data)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("admin/book_form.html", form=form, book=book)
            delete_cover_image(book.cover_image)
            book.cover_image = new_cover

        book.title = form.title.data.strip()
        book.author = form.author.data.strip()
        book.publisher = (form.publisher.data or "").strip() or None
        book.year = form.year.data
        book.price = form.price.data
        book.stock = form.stock.data
        book.description = (form.description.data or "").strip() or None
        book.category_id = form.category_id.data
        db.session.commit()
        flash("Đã cập nhật sách.", "success")
        return redirect(url_for("admin.books_list"))

    return render_template("admin/book_form.html", form=form, book=book)


@admin_bp.post("/books/<int:book_id>/delete")
def books_delete(book_id):
    form = CSRFOnlyForm()
    if not form.validate_on_submit():
        flash("Yêu cầu không hợp lệ.", "danger")
        return redirect(url_for("admin.books_list"))

    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    in_order = db.session.scalar(
        select(func.count(OrderItem.id)).where(OrderItem.book_id == book.id)
    )
    if in_order:
        flash(
            f"Không thể xoá «{book.title}» vì đã có trong đơn hàng.",
            "danger",
        )
        return redirect(url_for("admin.books_list"))

    delete_cover_image(book.cover_image)
    db.session.delete(book)
    db.session.commit()
    flash("Đã xoá sách.", "success")
    return redirect(url_for("admin.books_list"))


# ---------- Danh mục ----------


@admin_bp.route("/categories", methods=["GET", "POST"])
def categories_list():
    edit_id = request.values.get("edit", type=int)
    category = db.session.get(Category, edit_id) if edit_id else None
    form = CategoryForm(category_id=category.id if category else None)
    csrf_form = CSRFOnlyForm()

    if request.method == "GET" and category:
        form.name.data = category.name
        form.description.data = category.description

    if form.validate_on_submit():
        name = form.name.data.strip()
        description = (form.description.data or "").strip() or None
        if category:
            category.name = name
            category.description = description
            flash("Đã cập nhật danh mục.", "success")
        else:
            db.session.add(Category(name=name, description=description))
            flash("Đã thêm danh mục.", "success")
        db.session.commit()
        return redirect(url_for("admin.categories_list"))

    rows = db.session.execute(
        select(
            Category,
            func.count(Book.id).label("book_count"),
        )
        .outerjoin(Book, Book.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    ).all()

    return render_template(
        "admin/categories.html",
        rows=rows,
        form=form,
        csrf_form=csrf_form,
        editing=category,
    )


@admin_bp.post("/categories/<int:category_id>/delete")
def categories_delete(category_id):
    form = CSRFOnlyForm()
    if not form.validate_on_submit():
        flash("Yêu cầu không hợp lệ.", "danger")
        return redirect(url_for("admin.categories_list"))

    category = db.session.get(Category, category_id)
    if not category:
        abort(404)

    book_count = (
        db.session.scalar(
            select(func.count(Book.id)).where(Book.category_id == category.id)
        )
        or 0
    )
    if book_count > 0:
        flash(
            f"Không thể xoá «{category.name}»: còn {book_count} sách.",
            "danger",
        )
        return redirect(url_for("admin.categories_list"))

    db.session.delete(category)
    db.session.commit()
    flash("Đã xoá danh mục.", "success")
    return redirect(url_for("admin.categories_list"))


# ---------- Đơn hàng ----------


@admin_bp.get("/orders")
def orders_list():
    status = request.args.get("status") or ""
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    status_counts = dict(
        db.session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        ).all()
    )
    total_all = sum(status_counts.values())

    stmt = select(Order).order_by(Order.created_at.desc())
    if status in ORDER_STATUSES:
        stmt = stmt.where(Order.status == status)
    if q:
        like = f"%{q}%"
        filters = [
            Order.customer_name.ilike(like),
            Order.phone.ilike(like),
        ]
        if q.lstrip("#").isdigit():
            filters.append(Order.id == int(q.lstrip("#")))
        stmt = stmt.where(or_(*filters))

    filtered = db.session.execute(stmt).scalars().all()
    total = len(filtered)
    total_value = sum(o.total for o in filtered)
    orders = filtered[(page - 1) * per_page : page * per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "admin/orders_list.html",
        orders=orders,
        status=status,
        q=q,
        page=page,
        total=total,
        total_pages=total_pages,
        total_value=total_value,
        status_counts=status_counts,
        total_all=total_all,
        statuses=ORDER_STATUSES,
    )


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
def order_detail(order_id):
    order = db.session.execute(
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.book),
            joinedload(Order.history),
        )
        .where(Order.id == order_id)
    ).unique().scalar_one_or_none()
    if not order:
        abort(404)

    allowed = STATUS_TRANSITIONS.get(order.status, set())
    form = OrderStatusForm()
    form.status.choices = [(s, s) for s in allowed]
    csrf_form = CSRFOnlyForm()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "cancel":
            if not csrf_form.validate_on_submit():
                flash("Yêu cầu không hợp lệ.", "danger")
                return redirect(url_for("admin.order_detail", order_id=order.id))
            if ORDER_STATUS_CANCELLED not in allowed:
                flash("Không thể huỷ đơn ở trạng thái hiện tại.", "danger")
                return redirect(url_for("admin.order_detail", order_id=order.id))
            _cancel_order(order)
            flash("Đã huỷ đơn và hoàn tồn kho.", "success")
            return redirect(url_for("admin.order_detail", order_id=order.id))

        if action == "update":
            if not form.validate_on_submit():
                flash("Trạng thái không hợp lệ.", "danger")
                return redirect(url_for("admin.order_detail", order_id=order.id))
            new_status = form.status.data
            if new_status not in allowed:
                flash("Không thể chuyển sang trạng thái này.", "danger")
                return redirect(url_for("admin.order_detail", order_id=order.id))
            if new_status == ORDER_STATUS_CANCELLED:
                _cancel_order(order)
            else:
                order.status = new_status
                db.session.add(
                    OrderStatusHistory(order_id=order.id, status=new_status)
                )
                db.session.commit()
            flash("Đã cập nhật trạng thái đơn hàng.", "success")
            return redirect(url_for("admin.order_detail", order_id=order.id))

    editable = bool(allowed)
    return render_template(
        "admin/order_detail.html",
        order=order,
        form=form,
        csrf_form=csrf_form,
        editable=editable,
        can_cancel=ORDER_STATUS_CANCELLED in allowed,
    )


def _cancel_order(order: Order) -> None:
    if order.status == ORDER_STATUS_CANCELLED:
        return
    for item in order.items:
        if item.book:
            item.book.stock += item.quantity
    order.status = ORDER_STATUS_CANCELLED
    db.session.add(
        OrderStatusHistory(order_id=order.id, status=ORDER_STATUS_CANCELLED)
    )
    db.session.commit()
