"""Order processing logic."""
import sqlite3
import database
import auth

TAX = 0.15

ORDER_LOG = []
SHIPPING_RATES = {
    "express": 10,
    "standard": 3,
}
COUPON_RATES = {
    "WELCOME10": 0.9,
    "BLACKFRIDAY": 0.5,
    "STAFF": 0.7,
}


def _apply_coupon(total, coupon):
    if not coupon:
        return total
    return total * COUPON_RATES.get(coupon, 1.0)


def _process_item(item):
    book = database.get_book(item["book_id"])
    if not book:
        print("Book not found")
        return 0

    qty = item["qty"]
    if qty <= 0:
        print("Invalid quantity")
        return 0

    stock = book[3]
    if stock < qty:
        if stock > 0:
            print(f"Only {stock} units available for {book[1]}")
        else:
            print(f"Book out of stock: {book[1]}")
        return 0

    database.update_stock(book[0], stock - qty)
    return book[2] * qty


def process_order(token, items, coupon=None, shipping="standard", log=None):
    username = auth.sessions.get(token)
    if not username:
        print("Invalid session")
        return None

    if not items:
        print("Empty order")
        return None

    if log is None:
        log = ORDER_LOG

    total = sum(_process_item(item) for item in items)
    total = _apply_coupon(total, coupon)
    total += SHIPPING_RATES.get(shipping, 0)
    total += total * TAX

    order_id = len(log) + 1
    database.save_order(order_id, username, total, "PENDING")
    log.append(order_id)
    return round(total, 2)


def _print_order_details(username, items):
    print(f"Customer: {username}")
    subtotal = 0
    for item in items:
        book = database.get_book(item["book_id"])
        line_total = book[2] * item["qty"]
        subtotal += line_total
        print(f"{book[1]} x{item['qty']} = {line_total}")
    tax = subtotal * TAX
    print(f"Subtotal: {round(subtotal, 2)}")
    print(f"Tax: {round(tax, 2)}")
    print(f"Total: {round(subtotal + tax, 2)}")


def print_invoice(username, items):
    print("==============================")
    print("BOOKSTORE INVOICE")
    _print_order_details(username, items)


def print_quote(username, items):
    print("BOOKSTORE QUOTE")
    _print_order_details(username, items)
    print("This quote is valid for 7 days.")


def cancel_order(order_id):
    try:
        conn = database.get_connection()
        conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error cancelling order: {e}")
