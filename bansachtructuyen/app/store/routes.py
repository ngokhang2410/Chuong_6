from flask import abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_, select

from app.cart import (
    add_to_cart,
    cart_subtotal,
    clear_cart,
    get_cart_items,
    quantity_in_cart,
    remove_from_cart,
    set_quantity,
)
from app.extensions import db
from app.forms import CSRFOnlyForm, CheckoutForm
from app.models import (
    ORDER_STATUS_PENDING,
    Book,
    Category,
    Order,
    OrderItem,
    OrderStatusHistory,
)
from app.store import store_bp


@store_bp.get("/")
def index():
    return redirect(url_for("store.books_list"))


@store_bp.get("/books")
def books_list():
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category_id", type=int)

    stmt = select(Book).order_by(Book.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Book.title.ilike(like), Book.author.ilike(like)))
    if category_id:
        stmt = stmt.where(Book.category_id == category_id)

    books = db.session.execute(stmt).scalars().all()
    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()
    form = CSRFOnlyForm()

    return render_template(
        "store/books_list.html",
        books=books,
        categories=categories,
        q=q,
        category_id=category_id,
        form=form,
    )


@store_bp.route("/books/<int:book_id>", methods=["GET", "POST"])
def book_detail(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    form = CSRFOnlyForm()
    in_cart = quantity_in_cart(book.id)
    max_add = max(0, book.stock - in_cart)

    if request.method == "POST":
        if not form.validate_on_submit():
            flash("Yêu cầu không hợp lệ.", "danger")
            return redirect(url_for("store.book_detail", book_id=book.id))

        try:
            qty = int(request.form.get("quantity", 1))
        except (TypeError, ValueError):
            qty = 0

        if qty < 1 or qty > max_add:
            flash(
                f"Số lượng không hợp lệ. Chỉ có thể thêm tối đa {max_add} cuốn.",
                "danger",
            )
            return redirect(url_for("store.book_detail", book_id=book.id))

        add_to_cart(book.id, qty)
        flash(f"Đã thêm {qty} x {book.title} vào giỏ hàng.", "success")
        return redirect(url_for("store.book_detail", book_id=book.id))

    return render_template(
        "store/book_detail.html",
        book=book,
        form=form,
        in_cart=in_cart,
        max_add=max_add,
    )


@store_bp.post("/cart/add/<int:book_id>")
def cart_add(book_id):
    form = CSRFOnlyForm()
    if not form.validate_on_submit():
        flash("Yêu cầu không hợp lệ.", "danger")
        return redirect(request.referrer or url_for("store.books_list"))

    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    in_cart = quantity_in_cart(book.id)
    if book.stock <= 0 or in_cart >= book.stock:
        flash(f"«{book.title}» đã hết hàng hoặc vượt tồn kho.", "warning")
        return redirect(request.referrer or url_for("store.books_list"))

    add_to_cart(book.id, 1)
    flash(f"Đã thêm «{book.title}» vào giỏ hàng.", "success")
    return redirect(request.referrer or url_for("store.books_list"))


@store_bp.route("/cart", methods=["GET", "POST"])
def cart_view():
    form = CSRFOnlyForm()
    items = get_cart_items()

    if request.method == "POST":
        if not form.validate_on_submit():
            flash("Yêu cầu không hợp lệ.", "danger")
            return redirect(url_for("store.cart_view"))

        action = request.form.get("action")
        book_id = request.form.get("book_id", type=int)

        if action == "clear":
            clear_cart()
            flash("Đã xoá toàn bộ giỏ hàng.", "success")
            return redirect(url_for("store.cart_view"))

        if not book_id:
            flash("Thiếu thông tin sách.", "danger")
            return redirect(url_for("store.cart_view"))

        book = db.session.get(Book, book_id)
        if not book:
            remove_from_cart(book_id)
            flash("Sách không còn tồn tại, đã xoá khỏi giỏ.", "warning")
            return redirect(url_for("store.cart_view"))

        current_qty = quantity_in_cart(book_id)

        if action == "inc":
            if current_qty >= book.stock:
                flash(f"«{book.title}» chỉ còn {book.stock} cuốn.", "warning")
            else:
                set_quantity(book_id, current_qty + 1)
        elif action == "dec":
            set_quantity(book_id, current_qty - 1)
        elif action == "remove":
            remove_from_cart(book_id)
            flash(f"Đã xoá «{book.title}» khỏi giỏ.", "success")
        else:
            flash("Thao tác không hợp lệ.", "danger")

        return redirect(url_for("store.cart_view"))

    subtotal = cart_subtotal(items)
    return render_template(
        "store/cart.html",
        items=items,
        subtotal=subtotal,
        form=form,
    )


@store_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = get_cart_items()
    if not items:
        flash("Giỏ hàng trống. Vui lòng chọn sách trước khi đặt hàng.", "warning")
        return redirect(url_for("store.cart_view"))

    form = CheckoutForm()
    subtotal = cart_subtotal(items)
    shipping_fee = (
        0
        if subtotal >= current_app.config["FREE_SHIPPING_THRESHOLD"]
        else current_app.config["SHIPPING_FEE"]
    )
    total = subtotal + shipping_fee

    if form.validate_on_submit():
        # Kiểm tra tồn kho trước khi tạo đơn
        for item in items:
            book = item["book"]
            if item["quantity"] > book.stock:
                flash(
                    f"Không đủ hàng cho «{book.title}»: "
                    f"cần {item['quantity']}, còn {book.stock}.",
                    "danger",
                )
                return redirect(url_for("store.cart_view"))

        order = Order(
            customer_name=form.customer_name.data.strip(),
            phone=form.phone.data.strip(),
            email=(form.email.data or "").strip() or None,
            address=form.address.data.strip(),
            note=(form.note.data or "").strip() or None,
            payment_method=form.payment_method.data,
            status=ORDER_STATUS_PENDING,
            shipping_fee=shipping_fee,
            total=total,
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            book = item["book"]
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    book_id=book.id,
                    unit_price=book.price,
                    quantity=item["quantity"],
                )
            )
            book.stock -= item["quantity"]

        db.session.add(
            OrderStatusHistory(order_id=order.id, status=ORDER_STATUS_PENDING)
        )
        db.session.commit()
        clear_cart()
        flash("Đặt hàng thành công!", "success")
        return redirect(url_for("store.order_success", order_id=order.id))

    return render_template(
        "store/checkout.html",
        form=form,
        items=items,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=total,
    )


@store_bp.get("/orders/<int:order_id>")
def order_success(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    return render_template("store/order_success.html", order=order)
