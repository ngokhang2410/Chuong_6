from flask import session

from app.extensions import db
from app.models import Book


def _get_raw_cart() -> dict:
    return session.setdefault("cart", {})


def get_cart() -> dict[int, int]:
    """Trả về {book_id: quantity} với key là int."""
    raw = _get_raw_cart()
    return {int(k): int(v) for k, v in raw.items() if int(v) > 0}


def save_cart(cart: dict[int, int]) -> None:
    session["cart"] = {str(k): int(v) for k, v in cart.items() if int(v) > 0}
    session.modified = True


def cart_count() -> int:
    return sum(get_cart().values())


def cart_unique_count() -> int:
    return len(get_cart())


def add_to_cart(book_id: int, quantity: int = 1) -> None:
    cart = get_cart()
    cart[book_id] = cart.get(book_id, 0) + quantity
    save_cart(cart)


def set_quantity(book_id: int, quantity: int) -> None:
    cart = get_cart()
    if quantity <= 0:
        cart.pop(book_id, None)
    else:
        cart[book_id] = quantity
    save_cart(cart)


def remove_from_cart(book_id: int) -> None:
    cart = get_cart()
    cart.pop(book_id, None)
    save_cart(cart)


def clear_cart() -> None:
    session["cart"] = {}
    session.modified = True


def get_cart_items() -> list[dict]:
    """Lấy giá mới từ DB; không lưu giá trong session."""
    cart = get_cart()
    if not cart:
        return []

    books = db.session.execute(
        db.select(Book).where(Book.id.in_(cart.keys()))
    ).scalars().all()
    book_map = {b.id: b for b in books}

    items = []
    for book_id, qty in cart.items():
        book = book_map.get(book_id)
        if not book:
            continue
        items.append(
            {
                "book": book,
                "quantity": qty,
                "unit_price": book.price,
                "subtotal": book.price * qty,
            }
        )
    return items


def cart_subtotal(items: list[dict] | None = None) -> int:
    if items is None:
        items = get_cart_items()
    return sum(i["subtotal"] for i in items)


def quantity_in_cart(book_id: int) -> int:
    return get_cart().get(book_id, 0)
